from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import json
import traceback
import uuid
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import sys
import os


from lexer import Lexer
from parser import Parser, SemanticAnalyzer
from interpreter import Interpreter
from errors import SimpleSyntaxError, SemanticError

app = FastAPI(title="Simple Language IDE", version="1.0.0")


class CodeRequest(BaseModel):
    code: str

class CompileResponse(BaseModel):
    success: bool
    errors: Optional[List[str]] = None
    ast: Optional[Dict[str, Any]] = None
    tokens: Optional[List[Dict[str, Any]]] = None

class ExecuteResponse(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_id: Optional[str] = None


active_executions: Dict[str, Dict[str, Any]] = {}


class WebInterpreter(Interpreter):
    def __init__(self, program, websocket=None):
        super().__init__(program)
        self.websocket = websocket
        self.output_buffer = StringIO()
        self.input_queue = asyncio.Queue()
        self.waiting_for_input = False

    async def run_async(self):
        from meu_ast import InputStatement, PrintStatement, LetStatement
        from meu_ast import GotoStatement, IfGotoStatement, EndStatement, RemStatement
        
        try:
            while self.pc < len(self.line_numbers):
                line_num = self.line_numbers[self.pc]
                stmt = self.program.lines[line_num]
                
                print(f"[DEBUG] Executando linha {line_num}: {type(stmt).__name__}")
                
                if isinstance(stmt, InputStatement):
                    await self._handle_input_async(stmt)
                elif isinstance(stmt, PrintStatement):
                    val = self._get_variable(stmt.var)
                    await self._output(str(val))
                    self.pc += 1
                elif isinstance(stmt, LetStatement):
                    val = self._evaluate_expr(stmt.expr)
                    self._set_variable(stmt.var, val)
                    self.pc += 1
                elif isinstance(stmt, GotoStatement):
                    if stmt.target not in self.line_to_index:
                        raise RuntimeError(f"Linha {stmt.target} não existe (goto na linha {stmt.line})")
                    self.pc = self.line_to_index[stmt.target]
                elif isinstance(stmt, IfGotoStatement):
                    condition = self._evaluate_condition(stmt.left, stmt.op, stmt.right)
                    if condition:
                        if stmt.target not in self.line_to_index:
                            raise RuntimeError(f"Linha {stmt.target} não existe (if/goto na linha {stmt.line})")
                        self.pc = self.line_to_index[stmt.target]
                    else:
                        self.pc += 1
                elif isinstance(stmt, EndStatement):
                    break
                elif isinstance(stmt, RemStatement):
                    self.pc += 1
                else:
                    raise RuntimeError(f"Comando desconhecido na linha {line_num}")
                    
                await asyncio.sleep(0.001)
                
        except Exception as e:
            print(f"[DEBUG] Exceção durante execução: {type(e).__name__}: {e}")
            await self._output(f"ERRO DE EXECUÇÃO: {e}")
            raise

    async def _handle_input_async(self, stmt):
        if self.websocket:
            self.waiting_for_input = True
            await self.websocket.send_json({
                "type": "input_request", 
                "message": "? ",
                "variable": stmt.var
            })
            try:
                input_value = await asyncio.wait_for(self.input_queue.get(), timeout=30.0)
                input_str = str(input_value).strip()
                if not input_str:
                    raise ValueError("Entrada vazia")
                val = int(input_str)
                self._set_variable(stmt.var, val)
                self.waiting_for_input = False
                self.pc += 1
            except ValueError as e:
                self.waiting_for_input = False
                await self._output(f"ERRO: Entrada deve ser um número inteiro válido (recebido: '{input_value}')")
                raise RuntimeError("Entrada deve ser um número inteiro")
            except asyncio.TimeoutError:
                self.waiting_for_input = False
                await self._output("ERRO: Timeout - muito tempo sem resposta")
                raise RuntimeError("Timeout na entrada de dados")
        else:
            raise RuntimeError("Input não suportado em execução síncrona")

    async def _output(self, text):
        self.output_buffer.write(text + "\n")
        if self.websocket:
            await self.websocket.send_json({
                "type": "output", 
                "data": text
            })

    async def provide_input(self, value):
        await self.input_queue.put(value)

from meu_ast import *

def ast_to_dict(node):
    """Converte nós AST para dicionários serializáveis"""
    if isinstance(node, Program):
        return {
            "type": "Program",
            "lines": {str(k): ast_to_dict(v) for k, v in node.lines.items()}
        }
    elif isinstance(node, InputStatement):
        return {"type": "InputStatement", "var": node.var, "line": node.line}
    elif isinstance(node, PrintStatement):
        return {"type": "PrintStatement", "var": node.var, "line": node.line}
    elif isinstance(node, LetStatement):
        return {
            "type": "LetStatement", 
            "var": node.var, 
            "expr": ast_to_dict(node.expr),
            "line": node.line
        }
    elif isinstance(node, GotoStatement):
        return {"type": "GotoStatement", "target": node.target, "line": node.line}
    elif isinstance(node, IfGotoStatement):
        return {
            "type": "IfGotoStatement",
            "left": ast_to_dict(node.left),
            "op": node.op,
            "right": ast_to_dict(node.right),
            "target": node.target,
            "line": node.line
        }
    elif isinstance(node, EndStatement):
        return {"type": "EndStatement", "line": node.line}
    elif isinstance(node, RemStatement):
        return {"type": "RemStatement", "line": node.line}
    elif isinstance(node, BinaryOp):
        return {
            "type": "BinaryOp",
            "left": ast_to_dict(node.left),
            "op": node.op,
            "right": ast_to_dict(node.right)
        }
    elif isinstance(node, Number):
        return {"type": "Number", "value": node.value}
    elif isinstance(node, Variable):
        return {"type": "Variable", "name": node.name}
    else:
        return {"type": "Unknown", "value": str(node)}

@app.post("/api/compile", response_model=CompileResponse)
async def compile_code(request: CodeRequest):
    """Compila o código Simple e retorna tokens e AST"""
    try:
        lexer = Lexer(request.code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        program = parser.parse_program()
        
        analyzer = SemanticAnalyzer(program)
        analyzer.analyze()
        
        token_list = []
        for token in tokens:
            token_list.append({
                "type": token.type.name,
                "value": token.value,
                "line": token.line,
                "column": token.column
            })
        
        return CompileResponse(
            success=True,
            tokens=token_list,
            ast=ast_to_dict(program)
        )
        
    except (SyntaxError, SemanticError, Exception) as e:
        return CompileResponse(
            success=False,
            errors=[str(e)]
        )

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_code(request: CodeRequest):
    """Executa o código Simple de forma síncrona (sem input interativo)"""
    try:
        lexer = Lexer(request.code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse_program()
        analyzer = SemanticAnalyzer(program)
        analyzer.analyze()
        
        output_buffer = StringIO()
        error_buffer = StringIO()
        
        with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
            interpreter = Interpreter(program)
            
            original_input = __builtins__['input']
            def mock_input(prompt):
                raise RuntimeError("Input interativo não suportado em execução síncrona. Use execução WebSocket.")
            
            __builtins__['input'] = mock_input
            
            try:
                interpreter.run()
            finally:
                __builtins__['input'] = original_input
        
        output = output_buffer.getvalue()
        error = error_buffer.getvalue()
        
        if error:
            return ExecuteResponse(success=False, error=error.strip())
        
        return ExecuteResponse(success=True, output=output.strip())
        
    except Exception as e:
        return ExecuteResponse(success=False, error=str(e))

@app.websocket("/api/execute-interactive")
async def execute_interactive(websocket: WebSocket):
    """Executa código com suporte a input interativo via WebSocket"""
    await websocket.accept()
    execution_id = str(uuid.uuid4())
    interpreter = None
    
    async def message_handler():
        """Processa mensagens do WebSocket em paralelo"""
        try:
            while True:
                data = await websocket.receive_json()
                print(f"[DEBUG] Mensagem recebida: {data}")
                
                if data.get("type") == "input":
                    input_value = data.get("value", "")
                    print(f"[DEBUG] Input recebido: {repr(input_value)}")
                    if interpreter and interpreter.waiting_for_input:
                        await interpreter.provide_input(input_value)
                    else:
                        print(f"[DEBUG] Input recebido mas interpretador não está aguardando")
                elif data.get("type") == "stop":
                    print(f"[DEBUG] Comando de parada recebido")
                    if interpreter:
                        interpreter.should_stop = True
                    break
        except WebSocketDisconnect:
            print(f"[DEBUG] WebSocket desconectado no handler")
            if interpreter:
                interpreter.should_stop = True
        except Exception as e:
            print(f"[DEBUG] Erro no message handler: {e}")
    
    try:
        data = await websocket.receive_json()
        code = data.get("code", "")
        
        print(f"[DEBUG] Recebido código para execução: {repr(code)}")
        
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse_program()
        analyzer = SemanticAnalyzer(program)
        analyzer.analyze()
        
        print(f"[DEBUG] Compilação bem-sucedida")
        
        interpreter = WebInterpreter(program, websocket)
        active_executions[execution_id] = {
            "interpreter": interpreter,
            "websocket": websocket
        }
        
        await websocket.send_json({
            "type": "execution_started",
            "execution_id": execution_id
        })
        
        message_task = asyncio.create_task(message_handler())
        
        try:
            print(f"[DEBUG] Iniciando execução...")
            await interpreter.run_async()
            print(f"[DEBUG] Execução concluída com sucesso")
            await websocket.send_json({
                "type": "execution_finished",
                "success": True
            })
        except Exception as e:
            print(f"[DEBUG] Erro durante execução: {type(e).__name__}: {e}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            await websocket.send_json({
                "type": "execution_finished",
                "success": False,
                "error": str(e)
            })
        finally:
            message_task.cancel()
            try:
                await message_task
            except asyncio.CancelledError:
                pass
                
    except WebSocketDisconnect:
        print(f"[DEBUG] WebSocket desconectado durante inicialização")
        pass
    except Exception as e:
        print(f"[DEBUG] Erro geral: {type(e).__name__}: {e}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"{type(e).__name__}: {str(e)}"
            })
        except:
            pass
    finally:
        if execution_id in active_executions:
            del active_executions[execution_id]

@app.get("/api/examples")
async def get_examples():
    """Retorna exemplos de código Simple"""
    examples = {
        "hello": {
            "name": "Hello World",
            "code": """10 print h
20 end"""
        },
        "simple_input": {
            "name": "Teste de Input Simples",
            "code": """10 input a
20 print a
30 end"""
        },
        "sum": {
            "name": "Soma de dois números",
            "code": """10 input a
20 input b
30 let c = a + b
40 print c
50 end"""
        },
        "factorial": {
            "name": "Fatorial",
            "code": """10 input n
20 let f = 1
30 let i = 1
40 if i > n goto 80
50 let f = f * i
60 let i = i + 1
70 goto 40
80 print f
90 end"""
        },
        "fibonacci": {
            "name": "Sequência de Fibonacci",
            "code": """10 input n
20 let a = 0
30 let b = 1
40 let i = 0
50 if i >= n goto 120
60 print a
70 let t = a + b
80 let a = b
90 let b = t
100 let i = i + 1
110 goto 50
120 end"""
        }
    }
    return examples

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)