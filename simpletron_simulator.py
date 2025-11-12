from io import StringIO

class Simpletron:
    """
    Simula uma máquina Simpletron com 100 palavras de memória e um acumulador.
    """
    def __init__(self, sml_code, input_stream=None):
        # Constantes de operação
        self.READ = 10
        self.WRITE = 11
        self.LOAD = 20
        self.STORE = 21
        self.ADD = 30
        self.SUBTRACT = 31
        self.DIVIDE = 32
        self.MULTIPLY = 33
        self.BRANCH = 40
        self.BRANCHNEG = 41
        self.BRANCHZERO = 42
        self.HALT = 43

        self.memory = list(sml_code)
        # Garante que a memória tenha sempre 100 posições
        self.memory.extend([0] * (100 - len(self.memory)))
        
        self.accumulator = 0
        self.instruction_counter = 0
        self.operation_code = 0
        self.operand = 0
        
        self.input_stream = input_stream
        self.output_buffer = StringIO()

    def run(self):
        """
        Executa o programa SML carregado na memória até encontrar a instrução HALT.
        """
        while self.instruction_counter < len(self.memory):
            instruction_register = self.memory[self.instruction_counter]

            # Decodifica a instrução
            self.operation_code = instruction_register // 100
            self.operand = instruction_register % 100

            if self.operation_code == self.HALT:
                break
            
            # Executa a instrução
            self._execute_instruction()

        return self.output_buffer.getvalue()

    def _execute_instruction(self):
        """
        Mapeia o código de operação para a função correspondente.
        """
        op_map = {
            self.READ: self._read,
            self.WRITE: self._write,
            self.LOAD: self._load,
            self.STORE: self._store,
            self.ADD: self._add,
            self.SUBTRACT: self._subtract,
            self.DIVIDE: self._divide,
            self.MULTIPLY: self._multiply,
            self.BRANCH: self._branch,
            self.BRANCHNEG: self._branchneg,
            self.BRANCHZERO: self._branchzero,
        }

        if self.operation_code in op_map:
            op_map[self.operation_code]()
        else:
            raise ValueError(f"Instrução desconhecida ({self.operation_code:02d}) no endereço {self.instruction_counter:02d}")

    def _read(self):
        if self.input_stream is None:
            raise RuntimeError("Operação READ encontrada, mas nenhuma entrada foi fornecida.")
        try:
            value = int(self.input_stream.pop(0))
            if not -9999 <= value <= 9999:
                raise ValueError("Valor de entrada fora do intervalo [-9999, 9999].")
            self.memory[self.operand] = value
            self.instruction_counter += 1
        except (ValueError, IndexError):
            raise RuntimeError("Entrada inválida ou insuficiente.")

    def _write(self):
        value = self.memory[self.operand]
        self.output_buffer.write(f"{value}\n")
        self.instruction_counter += 1

    def _load(self):
        self.accumulator = self.memory[self.operand]
        self.instruction_counter += 1

    def _store(self):
        self.memory[self.operand] = self.accumulator
        self.instruction_counter += 1

    def _add(self):
        self.accumulator += self.memory[self.operand]
        self._check_accumulator_overflow()
        self.instruction_counter += 1

    def _subtract(self):
        self.accumulator -= self.memory[self.operand]
        self._check_accumulator_overflow()
        self.instruction_counter += 1

    def _divide(self):
        divisor = self.memory[self.operand]
        if divisor == 0:
            raise ZeroDivisionError(f"Tentativa de divisão por zero no endereço {self.instruction_counter:02d}")
        self.accumulator //= divisor
        self.instruction_counter += 1

    def _multiply(self):
        self.accumulator *= self.memory[self.operand]
        self._check_accumulator_overflow()
        self.instruction_counter += 1

    def _branch(self):
        self.instruction_counter = self.operand

    def _branchneg(self):
        if self.accumulator < 0:
            self.instruction_counter = self.operand
        else:
            self.instruction_counter += 1

    def _branchzero(self):
        if self.accumulator == 0:
            self.instruction_counter = self.operand
        else:
            self.instruction_counter += 1
            
    def _check_accumulator_overflow(self):
        if not -9999 <= self.accumulator <= 9999:
            raise OverflowError(f"Estouro do acumulador no endereço {self.instruction_counter:02d}")