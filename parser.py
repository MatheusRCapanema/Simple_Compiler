from lexer import Token, TokenType
from meu_ast import *
from errors import SemanticError

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = tokens[0] if tokens else None
        self.current_line = 0

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    def expect(self, token_type, value=None):
        if not self.current_token or self.current_token.type != token_type:
            token_name = token_type.name if hasattr(token_type, 'name') else str(token_type)
            current_name = self.current_token.type.name if self.current_token and hasattr(self.current_token.type, 'name') else str(self.current_token.type if self.current_token else None)
            raise SyntaxError(
                f"Linha {self.current_token.line if self.current_token else '?'}:{self.current_token.column if self.current_token else '?'} - "
                f"Esperado {token_name}, encontrado {current_name}"
            )
        if value is not None and self.current_token.value != value:
            raise SyntaxError(
                f"Linha {self.current_token.line}:{self.current_token.column} - "
                f"Esperado '{value}', encontrado '{self.current_token.value}'"
            )
        token = self.current_token
        self.advance()
        return token

    def parse_simple_expression(self):
        """
        Parse uma expressão simples que pode ter no máximo UMA operação:
        - NUMBER
        - VARIABLE  
        - VARIABLE OP VARIABLE
        - VARIABLE OP NUMBER
        - NUMBER OP VARIABLE
        - NUMBER OP NUMBER
        - Unário: -NUMBER ou -VARIABLE
        """
        if self.current_token and self.current_token.type == TokenType.OP_ARITH and self.current_token.value == '-':
            self.advance()
            operand = self.parse_operand()
            return BinaryOp(Number(0), '-', operand)
        
        if self.current_token and self.current_token.type == TokenType.OP_ARITH and self.current_token.value == '+':
            self.advance()
            return self.parse_operand()
        
        left = self.parse_operand()
        
        if (self.current_token and 
            self.current_token.type == TokenType.OP_ARITH and 
            self.current_token.value in ('+', '-', '*', '/', '%')):
            
            op = self.current_token.value
            self.advance()
            right = self.parse_operand()
            
            if (self.current_token and 
                self.current_token.type == TokenType.OP_ARITH and 
                self.current_token.value in ('+', '-', '*', '/', '%')):
                raise SyntaxError(
                    f"Linha {self.current_token.line}:{self.current_token.column} - "
                    f"Expressão muito complexa: apenas uma operação é permitida por expressão. "
                    f"Use variáveis intermediárias para expressões complexas."
                )
            
            return BinaryOp(left, op, right)
        
        return left

    def parse_operand(self):
        """Parse um operando simples (NUMBER ou VARIABLE)"""
        if not self.current_token:
            raise SyntaxError("Fim inesperado do arquivo durante análise de expressão")
            
        if self.current_token.type == TokenType.NUMBER:
            value = self.current_token.value
            self.advance()
            return Number(value)
        elif self.current_token.type == TokenType.ID:
            name = self.current_token.value
            self.advance()
            return Variable(name)
        else:
            token_info = f"{self.current_token.type.name}('{self.current_token.value}')" if self.current_token else "None"
            raise SyntaxError(
                f"Linha {self.current_token.line if self.current_token else '?'}:{self.current_token.column if self.current_token else '?'} - "
                f"Expressão inválida: encontrado {token_info}, esperado NUMBER ou VARIABLE"
            )

    def parse_expression(self):
        """Alias para parse_simple_expression para compatibilidade"""
        return self.parse_simple_expression()

    def parse_statement(self, line_number):
        if self.current_token.type == TokenType.REM:
            self.advance()
            return RemStatement(line_number)
        
        elif self.current_token.type == TokenType.INPUT:
            self.advance()
            var = self.expect(TokenType.ID).value
            return InputStatement(var, line_number)
        
        elif self.current_token.type == TokenType.PRINT:
            self.advance()
            var = self.expect(TokenType.ID).value
            return PrintStatement(var, line_number)
        
        elif self.current_token.type == TokenType.LET:
            self.advance()
            var = self.expect(TokenType.ID).value
            self.expect(TokenType.OP_ARITH, '=')
            expr = self.parse_simple_expression()
            return LetStatement(var, expr, line_number)
        
        elif self.current_token.type == TokenType.GOTO:
            self.advance()
            target = self.expect(TokenType.NUMBER).value
            return GotoStatement(target, line_number)
        
        elif self.current_token.type == TokenType.IF:
            self.advance()
            left = self.parse_simple_expression()
            
            op = self.expect(TokenType.OP_REL).value
            
            right = self.parse_simple_expression()
            
            self.expect(TokenType.GOTO_KEYWORD, 'goto')
            
            target = self.expect(TokenType.NUMBER).value
            
            return IfGotoStatement(left, op, right, target, line_number)
        
        elif self.current_token.type == TokenType.END:
            self.advance()
            return EndStatement(line_number)
        
        else:
            raise SyntaxError(
                f"Linha {self.current_token.line}:{self.current_token.column} - "
                f"Comando inválido: {self.current_token.value}"
            )

    def parse_program(self):
        lines = {}
        previous_line_number = 0
        
        while self.current_token and self.current_token.type != TokenType.EOF:
            if self.current_token.type != TokenType.LINE_NUMBER:
                raise SyntaxError(
                    f"Linha {self.current_token.line}:{self.current_token.column} - "
                    f"Esperado número de linha"
                )
            line_number = self.current_token.value
            
            if line_number <= previous_line_number:
                raise SyntaxError(
                    f"Linha {self.current_token.line}:{self.current_token.column} - "
                    f"Número de linha {line_number} deve ser maior que o anterior ({previous_line_number}). "
                    f"Os números de linha devem estar em ordem crescente."
                )
            
            if line_number in lines:
                raise SyntaxError(
                    f"Linha {self.current_token.line}:{self.current_token.column} - "
                    f"Número de linha {line_number} já foi usado. "
                    f"Cada linha deve ter um número único."
                )
            
            previous_line_number = line_number
            self.advance()
            
            statement = self.parse_statement(line_number)
            lines[line_number] = statement
            
            while self.current_token and self.current_token.type == TokenType.NEWLINE:
                self.advance()
        
        return Program(lines)

class SemanticAnalyzer:
    def __init__(self, program):
        self.program = program
        self.errors = []
        self.valid_line_numbers = set(program.lines.keys())

    def analyze(self):
        for line_num, stmt in self.program.lines.items():
            if isinstance(stmt, GotoStatement):
                self._check_goto_target(stmt.target, line_num)
            elif isinstance(stmt, IfGotoStatement):
                self._check_goto_target(stmt.target, line_num)
        
        if self.errors:
            raise SemanticError("\n".join(self.errors))
    
    def _check_goto_target(self, target, current_line):
        if target not in self.valid_line_numbers:
            self.errors.append(
                f"Linha {current_line}: Destino de goto {target} não existe"
            )