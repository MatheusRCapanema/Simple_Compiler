class SimpleSyntaxError(SyntaxError):
    def __init__(self, message, line=None, column=None):
        super().__init__(message)
        self.line = line
        self.column = column

class SemanticError(Exception):
    pass

class RuntimeError(Exception):
    pass