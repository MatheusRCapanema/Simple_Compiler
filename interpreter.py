from meu_ast import *

class Interpreter:
    def __init__(self, program):
        self.program = program
        self.variables = {}
        self.pc = 0  
        self.line_numbers = sorted(program.lines.keys())
        self.line_to_index = {line: idx for idx, line in enumerate(self.line_numbers)}

    def _get_variable(self, name):
        return self.variables.get(name, 0)

    def _set_variable(self, name, value):
        self.variables[name] = value

    def _evaluate_expr(self, expr):
        if isinstance(expr, Number):
            return expr.value
        elif isinstance(expr, Variable):
            return self._get_variable(expr.name)
        elif isinstance(expr, BinaryOp):
            left_val = self._evaluate_expr(expr.left)
            right_val = self._evaluate_expr(expr.right)
            
            if expr.op == '+': return left_val + right_val
            if expr.op == '-': return left_val - right_val
            if expr.op == '*': return left_val * right_val
            if expr.op == '/': 
                if right_val == 0:
                    raise RuntimeError("Divisão por zero")
                return left_val // right_val 
            if expr.op == '%': 
                if right_val == 0:
                    raise RuntimeError("Divisão por zero")
                return left_val % right_val
            if expr.op == '=': return right_val
            raise RuntimeError(f"Operador desconhecido: {expr.op}")
        else:
            raise RuntimeError(f"Tipo de expressão inválido: {type(expr)}")

    def _evaluate_condition(self, left, op, right):
        left_val = self._evaluate_expr(left)
        right_val = self._evaluate_expr(right)
        
        if op == '==': return left_val == right_val
        if op == '!=': return left_val != right_val
        if op == '>': return left_val > right_val
        if op == '>=': return left_val >= right_val
        if op == '<': return left_val < right_val
        if op == '<=': return left_val <= right_val
        raise RuntimeError(f"Operador relacional inválido: {op}")

    def run(self):
        while self.pc < len(self.line_numbers):
            line_num = self.line_numbers[self.pc]
            stmt = self.program.lines[line_num]
            
            if isinstance(stmt, InputStatement):
                try:
                    val = int(input('? '))
                    self._set_variable(stmt.var, val)
                except ValueError:
                    raise RuntimeError("Entrada deve ser um número inteiro")
                self.pc += 1
                
            elif isinstance(stmt, PrintStatement):
                val = self._get_variable(stmt.var)
                print(val)
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
                condition = self._evaluate_condition(
                    stmt.left, stmt.op, stmt.right
                )
                if condition:
                    if stmt.target not in self.line_to_index:
                        raise RuntimeError(
                            f"Linha {stmt.target} não existe (if/goto na linha {stmt.line})"
                        )
                    self.pc = self.line_to_index[stmt.target]
                else:
                    self.pc += 1
                    
            elif isinstance(stmt, EndStatement):
                break
                
            elif isinstance(stmt, RemStatement):
                self.pc += 1
                
            else:
                raise RuntimeError(f"Comando desconhecido na linha {line_num}")