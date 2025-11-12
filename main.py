from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import traceback
import uuid
import os

from lexer import Lexer
from parser import Parser, SemanticAnalyzer
from interpreter import Interpreter
from sml_compiler import SMLCompiler
from simpletron_simulator import Simpletron
from errors import SemanticError

app = FastAPI(title="Simple Language IDE", version="1.0.0")

# --- Modelos de Dados ---
class CodeRequest(BaseModel):
    code: str

# --- Lógica Auxiliar e Classes Assíncronas ---

class WebSimpletron(Simpletron):
    """
    Versão assíncrona do Simpletron que se integra com WebSockets
    para I/O interativo.
    """
    def __init__(self, sml_code, websocket: WebSocket):
        super().__init__(sml_code, input_stream=[])
        self.websocket = websocket
        self.input_queue = asyncio.Queue()
        self.waiting_for_input = False

    async def run_async(self):
        """Executa o programa SML de forma assíncrona."""
        while self.instruction_counter < 100:
            instruction_register = self.memory[self.instruction_counter]
            self.operation_code = instruction_register // 100
            self.operand = instruction_register % 100

            if self.operation_code == self.HALT:
                break
            await self._execute_instruction_async()
            await asyncio.sleep(0.01)

    async def _execute_instruction_async(self):
        """Mapeia e executa uma instrução SML de forma assíncrona."""
        sync_ops = {
            self.LOAD: self._load, self.STORE: self._store,
            self.ADD: self._add, self.SUBTRACT: self._subtract,
            self.DIVIDE: self._divide, self.MULTIPLY: self._multiply,
            self.BRANCH: self._branch, self.BRANCHNEG: self._branchneg,
            self.BRANCHZERO: self._branchzero,
        }
        if self.operation_code == self.READ:
            await self._read_async()
        elif self.operation_code == self.WRITE:
            await self._write_async()
        elif self.operation_code in sync_ops:
            sync_ops[self.operation_code]()
        else:
            raise ValueError(f"Instrução SML desconhecida ({self.operation_code:02d})")

    async def _read_async(self):
        """Lida com a instrução READ de forma interativa."""
        self.waiting_for_input = True
        await self.websocket.send_json({
            "type": "input_request",
            "message": f"? (SML input para mem[{self.operand:02d}]) "
        })
        try:
            input_value = await asyncio.wait_for(self.input_queue.get(), timeout=120.0)
            value = int(str(input_value).strip())
            if not -9999 <= value <= 9999:
                raise ValueError("Valor de entrada fora do intervalo [-9999, 9999].")
            self.memory[self.operand] = value
            self.instruction_counter += 1
        except (ValueError, asyncio.TimeoutError) as e:
            await self.websocket.send_json({"type": "sml_output", "data": f"ERRO de entrada SML: {e}"})
            raise
        finally:
            self.waiting_for_input = False

    async def _write_async(self):
        """Lida com a instrução WRITE via WebSocket."""
        value = self.memory[self.operand]
        await self.websocket.send_json({"type": "sml_output", "data": str(value)})
        self.instruction_counter += 1

    async def provide_input(self, value):
        if self.waiting_for_input:
            await self.input_queue.put(value)


def detect_language(code: str) -> str:
    """Detecta se o código é Simple ou SML."""
    lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
    if not lines: return 'simple'
    first_line = lines[0]
    try:
        parts = first_line.split(':'); code_part = parts[-1].strip()
        if (code_part.startswith(('+', '-'))) and len(code_part) == 5:
            int(code_part); return 'sml'
    except (ValueError, IndexError): pass
    try:
        if first_line.split()[0].isdigit(): return 'simple'
    except IndexError: pass
    return 'sml'

async def handle_simple_execution(websocket: WebSocket, code: str):
    """Orquestra a execução de código Simple e a subsequente execução de SML."""
    interpreter = None
    collected_inputs = []
    async def message_handler():
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "input":
                    value = data.get("value", "")
                    collected_inputs.append(value)
                    if interpreter and interpreter.waiting_for_input:
                        await interpreter.provide_input(value)
                elif data.get("type") == "stop":
                    if interpreter: interpreter.should_stop = True
                    break
        except WebSocketDisconnect:
            if interpreter: interpreter.should_stop = True

    try:
        # Compila e traduz
        lexer, tokens = Lexer(code), []; tokens = lexer.tokenize()
        program = Parser(tokens).parse_program(); SemanticAnalyzer(program).analyze()
        sml_code = SMLCompiler(program).compile()
        formatted_sml = [f"{i:02d}: {c:+05d}" for i, c in enumerate(sml_code)]
        await websocket.send_json({"type": "sml_translation", "sml_code": formatted_sml})

        # Executa Simple
        interpreter = WebInterpreter(program, websocket)
        await websocket.send_json({"type": "execution_started"})
        message_task = asyncio.create_task(message_handler())
        await interpreter.run_async()
        message_task.cancel(); await asyncio.gather(message_task, return_exceptions=True)

        # Executa SML
        await websocket.send_json({"type": "sml_execution_started"})
        sml_output = Simpletron(sml_code, input_stream=collected_inputs).run()
        await websocket.send_json({"type": "sml_output", "data": sml_output or "(Nenhuma saída SML)"})
        await websocket.send_json({"type": "execution_finished", "success": True})

    except Exception as e:
        await websocket.send_json({"type": "execution_finished", "success": False, "error": f"{type(e).__name__}: {e}"})

async def handle_sml_execution(websocket: WebSocket, code: str):
    """Lida com a execução interativa de código SML."""
    sml_simulator = None
    async def message_handler():
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "input":
                    if sml_simulator and sml_simulator.waiting_for_input:
                        await sml_simulator.provide_input(data.get("value", ""))
                elif data.get("type") == "stop": break
        except WebSocketDisconnect: pass

    try:
        raw_memory = [0] * 100
        lines = [line.strip() for line in code.strip().split('\n') if line.strip()]
        for idx, line in enumerate(lines):
            parts = line.split(':')
            address = int(parts[0]) if len(parts) > 1 else idx
            if 0 <= address < 100: raw_memory[address] = int(parts[-1].strip())
        
        sml_simulator = WebSimpletron(raw_memory, websocket=websocket)
        await websocket.send_json({"type": "sml_execution_started"})
        message_task = asyncio.create_task(message_handler())
        await sml_simulator.run_async()
        message_task.cancel(); await asyncio.gather(message_task, return_exceptions=True)

        await websocket.send_json({"type": "execution_finished", "success": True})
        
    except Exception as e:
        await websocket.send_json({"type": "execution_finished", "success": False, "error": f"{type(e).__name__}: {e}"})

# --- Endpoints da API ---
@app.websocket("/api/execute-interactive")
async def execute_interactive(websocket: WebSocket):
    await websocket.accept()
    try:
        code = (await websocket.receive_json()).get("code", "")
        language = detect_language(code)
        if language == 'simple': await handle_simple_execution(websocket, code)
        else: await handle_sml_execution(websocket, code)
    except WebSocketDisconnect: pass
    except Exception as e:
        try: await websocket.send_json({"type": "error", "message": f"{type(e).__name__}: {e}"})
        except RuntimeError: pass

# ... (outros endpoints como /api/compile e /api/examples permanecem os mesmos) ...
@app.post("/api/compile")
async def compile_code(request: CodeRequest):
    try:
        lexer = Lexer(request.code); tokens = lexer.tokenize()
        program = Parser(tokens).parse_program(); SemanticAnalyzer(program).analyze()
        token_list = [{"type": t.type.name, "value": t.value, "line": t.line, "column": t.column} for t in tokens]
        from meu_ast import Program, InputStatement, PrintStatement, LetStatement, GotoStatement, IfGotoStatement, EndStatement, RemStatement, BinaryOp, Number, Variable
        def ast_to_dict(node):
            if not isinstance(node, (Program, InputStatement, PrintStatement, LetStatement, GotoStatement, IfGotoStatement, EndStatement, RemStatement, BinaryOp, Number, Variable)): return {"type": "Unknown", "value": str(node)}
            node_type = type(node).__name__
            result = {"type": node_type}
            if hasattr(node, '__dict__'):
                for key, value in node.__dict__.items():
                    if value is None: continue
                    if isinstance(value, (int, str, float, bool)): result[key] = value
                    elif isinstance(value, dict): result[key] = {str(k): ast_to_dict(v) for k, v in value.items()}
                    elif isinstance(value, list): result[key] = [ast_to_dict(v) for v in value]
                    else: result[key] = ast_to_dict(value)
            return result
        return {"success": True, "tokens": token_list, "ast": ast_to_dict(program)}
    except Exception as e:
        return {"success": False, "errors": [str(e)]}

@app.get("/api/examples")
async def get_examples():
    return {
        "sum": {"name": "Soma (Simple)", "code": "10 rem Soma de dois numeros\n20 input a\n30 input b\n40 let c = a + b\n50 print c\n60 end"},
        "comparison": {"name": "Maior de dois (Simple)", "code": "10 rem Compara qual numero e maior\n20 input a\n30 input b\n40 if a > b goto 70\n50 print b\n60 goto 80\n70 print a\n80 end"},
        "sml_example": {"name": "Soma (SML)", "code": "00: +1007\n01: +1008\n02: +2007\n03: +3008\n04: +2109\n05: +1109\n06: +4300"}
    }
# --- Configuração do App ---
from interpreter import Interpreter
from io import StringIO
class WebInterpreter(Interpreter):
    def __init__(self, program, websocket=None):
        super().__init__(program)
        self.websocket = websocket; self.output_buffer = StringIO(); self.input_queue = asyncio.Queue(); self.waiting_for_input = False; self.should_stop = False
    async def run_async(self):
        from meu_ast import InputStatement, PrintStatement, LetStatement, GotoStatement, IfGotoStatement, EndStatement, RemStatement
        try:
            while self.pc < len(self.line_numbers) and not self.should_stop:
                stmt = self.program.lines[self.line_numbers[self.pc]]
                if isinstance(stmt, InputStatement): await self._handle_input_async(stmt)
                elif isinstance(stmt, PrintStatement): await self._output(str(self._get_variable(stmt.var))); self.pc += 1
                elif isinstance(stmt, LetStatement): self._set_variable(stmt.var, self._evaluate_expr(stmt.expr)); self.pc += 1
                elif isinstance(stmt, GotoStatement): self.pc = self.line_to_index[stmt.target]
                elif isinstance(stmt, IfGotoStatement): self.pc = self.line_to_index[stmt.target] if self._evaluate_condition(stmt.left, stmt.op, stmt.right) else self.pc + 1
                elif isinstance(stmt, EndStatement): break
                elif isinstance(stmt, RemStatement): self.pc += 1
                else: raise RuntimeError(f"Comando desconhecido")
                await asyncio.sleep(0.01)
        except Exception as e: await self._output(f"ERRO: {e}"); raise
    async def _handle_input_async(self, stmt):
        self.waiting_for_input = True
        await self.websocket.send_json({"type": "input_request", "message": "? ", "variable": stmt.var})
        try:
            val = int(str(await asyncio.wait_for(self.input_queue.get(), timeout=120.0)).strip())
            self._set_variable(stmt.var, val); self.waiting_for_input = False; self.pc += 1
        except (ValueError, asyncio.TimeoutError) as e: self.waiting_for_input = False; await self._output(f"ERRO de entrada: {e}"); raise
    async def _output(self, text):
        if self.websocket: await self.websocket.send_json({"type": "output", "data": text})
    async def provide_input(self, value):
        if self.waiting_for_input: await self.input_queue.put(value)

if not os.path.exists("static"): os.makedirs("static")
if os.path.exists("index.html") and not os.path.exists("static/index.html"): import shutil; shutil.copy("index.html", "static/index.html")
app.mount("/", StaticFiles(directory="static", html=True), name="static")