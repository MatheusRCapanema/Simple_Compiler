class Program:
    def __init__(self, lines):
        self.lines = lines

class InputStatement:
    def __init__(self, var, line):
        self.var = var
        self.line = line

class PrintStatement:
    def __init__(self, var, line):
        self.var = var
        self.line = line

class LetStatement:
    def __init__(self, var, expr, line):
        self.var = var
        self.expr = expr
        self.line = line

class GotoStatement:
    def __init__(self, target, line):
        self.target = target
        self.line = line

class IfGotoStatement:
    def __init__(self, left, op, right, target, line):
        self.left = left
        self.op = op
        self.right = right
        self.target = target
        self.line = line

class EndStatement:
    def __init__(self, line):
        self.line = line

class RemStatement:
    def __init__(self, line):
        self.line = line

class BinaryOp:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class Number:
    def __init__(self, value):
        self.value = value

class Variable:
    def __init__(self, name):
        self.name = name

