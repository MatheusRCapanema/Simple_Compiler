from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    LINE_NUMBER = auto()
    REM = auto()
    INPUT = auto()
    LET = auto()
    PRINT = auto()
    GOTO = auto()
    IF = auto()
    END = auto()
    ID = auto()
    NUMBER = auto()
    OP_ARITH = auto()
    OP_REL = auto()
    GOTO_KEYWORD = auto()
    NEWLINE = auto()
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    column: int

class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self.source[0] if source else None

    def advance(self):
        if self.current_char == '\n':
            self.line += 1
            self.column = 0
        self.pos += 1
        self.column += 1
        if self.pos < len(self.source):
            self.current_char = self.source[self.pos]
        else:
            self.current_char = None

    def skip_whitespace(self):
        while self.current_char and self.current_char in ' \t':
            self.advance()

    def number(self):
        start_pos = self.pos
        while self.current_char and self.current_char.isdigit():
            self.advance()
        return int(self.source[start_pos:self.pos])

    def identifier(self):
        start_pos = self.pos
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            self.advance()
        return self.source[start_pos:self.pos]

    def tokenize_line_number(self):
        start_pos = self.pos
        while self.current_char and self.current_char.isdigit():
            self.advance()
        num = int(self.source[start_pos:self.pos])
        self.skip_whitespace()
        return num

    def tokenize(self):
        tokens = []
        in_if_statement = False
        
        while self.current_char:
            start_line = self.line
            start_column = self.column
            
            if self.pos == 0 or (self.pos > 0 and self.source[self.pos-1] == '\n' and self.current_char.isdigit()):
                line_num = self.tokenize_line_number()
                tokens.append(Token(TokenType.LINE_NUMBER, line_num, start_line, start_column))
                in_if_statement = False
                continue
            
            if self.current_char == '\n':
                tokens.append(Token(TokenType.NEWLINE, None, start_line, start_column))
                self.advance()
                in_if_statement = False
                continue
            
            if self.current_char in ' \t':
                self.skip_whitespace()
                continue
            
            if self.current_char.isalpha() and self.source[self.pos:self.pos+3].lower() == 'rem':
                tokens.append(Token(TokenType.REM, 'rem', start_line, start_column))
                while self.current_char and self.current_char != '\n':
                    self.advance()
                continue
            
            if self.current_char.isalpha():
                word = self.identifier().lower()
                if word == 'input':
                    tokens.append(Token(TokenType.INPUT, 'input', start_line, start_column))
                elif word == 'let':
                    tokens.append(Token(TokenType.LET, 'let', start_line, start_column))
                elif word == 'print':
                    tokens.append(Token(TokenType.PRINT, 'print', start_line, start_column))
                elif word == 'goto':
                    if in_if_statement:
                        tokens.append(Token(TokenType.GOTO_KEYWORD, 'goto', start_line, start_column))
                    else:
                        tokens.append(Token(TokenType.GOTO, 'goto', start_line, start_column))
                elif word == 'if':
                    tokens.append(Token(TokenType.IF, 'if', start_line, start_column))
                    in_if_statement = True
                elif word == 'end':
                    tokens.append(Token(TokenType.END, 'end', start_line, start_column))
                else:
                    if len(word) == 1 and word.islower():
                        tokens.append(Token(TokenType.ID, word, start_line, start_column))
                    else:
                        raise SyntaxError(
                            f"Linha {self.line}:{self.column} - "
                            f"Identificador inválido: '{word}' (deve ser 1 letra minúscula)"
                        )
                continue
            
            if self.current_char.isdigit():
                num = self.number()
                tokens.append(Token(TokenType.NUMBER, num, start_line, start_column))
                continue
            
            if self.current_char in '+-*/%':
                op = self.current_char
                self.advance()
                tokens.append(Token(TokenType.OP_ARITH, op, start_line, start_column))
                continue
            
            if self.current_char == '=':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    tokens.append(Token(TokenType.OP_REL, '==', start_line, start_column))
                else:
                    tokens.append(Token(TokenType.OP_ARITH, '=', start_line, start_column))
                continue
            
            if self.current_char in '<>!':
                op = self.current_char
                self.advance()
                if self.current_char == '=' and op in '<>!':
                    op += '='
                    self.advance()
                elif op == '!':
                    raise SyntaxError(
                        f"Linha {self.line}:{self.column} - "
                        f"Operador inválido: '!' (use '!=' para diferente)"
                    )
                tokens.append(Token(TokenType.OP_REL, op, start_line, start_column))
                continue
            
            raise SyntaxError(
                f"Linha {self.line}:{self.column} - "
                f"Caractere inválido: '{self.current_char}'"
            )
        
        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens