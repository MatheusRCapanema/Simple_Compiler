from meu_ast import *

READ = 10
WRITE = 11
LOAD = 20
STORE = 21
ADD = 30
SUBTRACT = 31
DIVIDE = 32
MULTIPLY = 33
BRANCH = 40
BRANCHNEG = 41
BRANCHZERO = 42
HALT = 43

class SMLCompiler:
    """
    Realiza a compilação de um programa em Simple (representado por uma AST)
    para o código de máquina do Simpletron (SML).
    
    OTIMIZAÇÃO: Aloca dados logo após o código (crescendo para frente)
    em vez de alocar do final da memória (crescendo para trás).
    """
    def __init__(self, program):
        self.program = program
        self.symbolic_code = []
        self.symbol_table = {}
        self.line_location_map = {}
        
    def compile(self):
        """
        Orquestra o processo de compilação em 3 passadas.
        """

        sorted_lines = sorted(self.program.lines.keys())
        for line_num in sorted_lines:
            self.line_location_map[line_num] = len(self.symbolic_code)
            stmt = self.program.lines[line_num]
            self._generate_code_for_statement(stmt)
        

        code_size = len(self.symbolic_code)
        data_start = code_size
        

        symbols_needed = set()
        self._discover_symbols(self.program, symbols_needed)
        

        data_pointer = data_start
        for symbol in sorted(symbols_needed):
            self.symbol_table[symbol] = data_pointer
            data_pointer += 1
        
        total_memory_needed = data_pointer
        if total_memory_needed > 100:
            raise MemoryError(
                f"Compilação falhou: Memória insuficiente!\n"
                f"  - Instruções: {code_size}\n"
                f"  - Símbolos: {len(symbols_needed)}\n"
                f"  - Total necessário: {total_memory_needed}\n"
                f"  - Memória disponível: 100"
            )
        
        final_code = [0] * total_memory_needed
        
        for name, address in self.symbol_table.items():
            if name.startswith('__const_'):
                try:
                    value = int(name.split('_')[-1])
                    if value < 0:
                        value = int(name.split('_')[-2] + name.split('_')[-1])
                    final_code[address] = value
                except (ValueError, IndexError):
                    raise ValueError(f"Erro ao processar constante: {name}")
        
        for i, (opcode, operand) in enumerate(self.symbolic_code):
            final_operand = 0
            
            if isinstance(operand, str):
                if operand not in self.symbol_table:
                    raise NameError(f"Símbolo não definido: '{operand}'")
                final_operand = self.symbol_table[operand]
                
            elif isinstance(operand, int):
                if opcode in (BRANCH, BRANCHNEG, BRANCHZERO):
                    final_operand = self.line_location_map.get(operand)
                    if final_operand is None:
                        raise ValueError(f"Destino de GOTO inválido: linha {operand}")
                else:
                    final_operand = operand
            
            final_code[i] = opcode * 100 + final_operand
        
        return final_code
    
    def _discover_symbols(self, node, symbols_set):
        """
        Percorre a AST recursivamente para encontrar todos os símbolos.
        """
        if isinstance(node, Program):
            for stmt in node.lines.values():
                self._discover_symbols(stmt, symbols_set)
                
        elif isinstance(node, (InputStatement, PrintStatement)):
            symbols_set.add(node.var)
            
        elif isinstance(node, LetStatement):
            symbols_set.add(node.var)
            self._discover_symbols(node.expr, symbols_set)
            
        elif isinstance(node, IfGotoStatement):
            self._discover_symbols(node.left, symbols_set)
            self._discover_symbols(node.right, symbols_set)
            
        elif isinstance(node, BinaryOp):
            self._discover_symbols(node.left, symbols_set)
            self._discover_symbols(node.right, symbols_set)
            
        elif isinstance(node, Variable):
            symbols_set.add(node.name)
            
        elif isinstance(node, Number):
            symbols_set.add(f"__const_{node.value}")
    
    def _get_operand_symbol(self, operand_node):
        """
        Retorna o nome do símbolo para um nó de operando.
        """
        if isinstance(operand_node, Variable):
            return operand_node.name
        elif isinstance(operand_node, Number):
            return f"__const_{operand_node.value}"
        raise TypeError(f"Tipo de operando inválido: {type(operand_node)}")
    
    def _emit(self, opcode, operand=None):
        """
        Adiciona uma instrução simbólica ao código intermediário.
        """
        self.symbolic_code.append((opcode, operand))
    
    def _generate_code_for_statement(self, stmt):
        """
        Gera código simbólico para um statement da AST.
        """
        if isinstance(stmt, RemStatement):
            return
        
        if isinstance(stmt, InputStatement):
            self._emit(READ, stmt.var)
            
        elif isinstance(stmt, PrintStatement):
            self._emit(WRITE, stmt.var)
            
        elif isinstance(stmt, EndStatement):
            self._emit(HALT, 0)
            
        elif isinstance(stmt, GotoStatement):
            self._emit(BRANCH, stmt.target)
        
        elif isinstance(stmt, LetStatement):
            var_symbol = stmt.var
            expr = stmt.expr
            
            if isinstance(expr, (Number, Variable)):
                expr_symbol = self._get_operand_symbol(expr)
                self._emit(LOAD, expr_symbol)
                
            elif isinstance(expr, BinaryOp):
                left_symbol = self._get_operand_symbol(expr.left)
                right_symbol = self._get_operand_symbol(expr.right)
                self._emit(LOAD, left_symbol)
                
                op_map = {
                    '+': ADD, 
                    '-': SUBTRACT, 
                    '*': MULTIPLY, 
                    '/': DIVIDE,
                    '%': MULTIPLY
                }
                
                if expr.op not in op_map:
                    raise ValueError(f"Operador não suportado: {expr.op}")
                    
                self._emit(op_map[expr.op], right_symbol)
            
            self._emit(STORE, var_symbol)
        
        elif isinstance(stmt, IfGotoStatement):
            left_symbol = self._get_operand_symbol(stmt.left)
            right_symbol = self._get_operand_symbol(stmt.right)
            
            if stmt.op == '==':
                self._emit(LOAD, left_symbol)
                self._emit(SUBTRACT, right_symbol)
                self._emit(BRANCHZERO, stmt.target)
                
            elif stmt.op == '<':
                self._emit(LOAD, left_symbol)
                self._emit(SUBTRACT, right_symbol)
                self._emit(BRANCHNEG, stmt.target)
                
            elif stmt.op == '>':
                self._emit(LOAD, right_symbol)
                self._emit(SUBTRACT, left_symbol)
                self._emit(BRANCHNEG, stmt.target)
            
            elif stmt.op == '!=':
                self._emit(LOAD, left_symbol)
                self._emit(SUBTRACT, right_symbol)
                next_instr = len(self.symbolic_code) + 2
                self._emit(BRANCHZERO, next_instr)
                self._emit(BRANCH, stmt.target)
                
            elif stmt.op == '>=':
                self._emit(LOAD, left_symbol)
                self._emit(SUBTRACT, right_symbol)
                next_instr = len(self.symbolic_code) + 2
                self._emit(BRANCHNEG, next_instr)
                self._emit(BRANCH, stmt.target)
                
            elif stmt.op == '<=':
                self._emit(LOAD, right_symbol)
                self._emit(SUBTRACT, left_symbol)
                next_instr = len(self.symbolic_code) + 2
                self._emit(BRANCHNEG, next_instr)
                self._emit(BRANCH, stmt.target)
                
            else:
                raise ValueError(f"Operador relacional não suportado: {stmt.op}")
                
        else:
            raise TypeError(f"Tipo de statement desconhecido: {type(stmt).__name__}")