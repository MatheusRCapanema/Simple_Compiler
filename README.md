# Simple Language IDE

A web-based Integrated Development Environment (IDE) for the Simple programming language, featuring real-time code execution, interactive input handling, and comprehensive debugging tools.

## Features

- **Modern Web IDE**: Clean, responsive interface with syntax highlighting
- **Dual Execution Modes**: 
  - Synchronous execution for programs without user input
  - Interactive execution with WebSocket support for real-time input/output
- **Code Analysis**: 
  - Token visualization
  - Abstract Syntax Tree (AST) display
  - Real-time compilation feedback
- **Built-in Examples**: Pre-loaded code samples demonstrating language features
- **Error Handling**: Comprehensive error reporting with line numbers and descriptions

## Simple Language Syntax

The Simple language supports BASIC-style programming with line numbers:

### Commands
- `INPUT variable` - Read integer input from user
- `PRINT variable` - Output variable value
- `LET variable = expression` - Variable assignment
- `GOTO line_number` - Unconditional jump
- `IF expression operator expression GOTO line_number` - Conditional jump
- `REM comment` - Comments (remainder of line ignored)
- `END` - Program termination

### Operators
- **Arithmetic**: `+`, `-`, `*`, `/`, `%`
- **Comparison**: `==`, `!=`, `>`, `>=`, `<`, `<=`

### Example Program
```
10 input a
20 input b  
30 let c = a + b
40 print c
50 end
```

## Architecture

### Backend (Python/FastAPI)
- **Lexer** (`lexer.py`): Tokenizes source code
- **Parser** (`parser.py`): Builds Abstract Syntax Tree with semantic analysis
- **Interpreter** (`interpreter.py`): Executes parsed programs
- **AST Nodes** (`meu_ast.py`): Abstract syntax tree node definitions
- **Error Handling** (`errors.py`): Custom exception classes

### Frontend (HTML/CSS/JavaScript)
- Modern, responsive web interface
- Real-time WebSocket communication for interactive execution
- Tabbed interface for output, AST, and token visualization
- Built-in code editor with line numbers

### API Endpoints
- `POST /api/compile` - Compile code and return AST/tokens
- `POST /api/execute` - Execute code synchronously
- `WebSocket /api/execute-interactive` - Interactive execution with input support
- `GET /api/examples` - Retrieve example programs

## Installation and Setup

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd simple-language-ide
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python run.py
   ```

4. **Access the IDE**
   Open your browser to `http://localhost:8000`

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t simple-ide .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 simple-ide
   ```

## Deployment

The application is ready for deployment on various platforms:

### Render.com (Recommended)
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Railway
- Automatic Python detection
- No additional configuration required

### Heroku
- Add `Procfile`: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`

## Technical Implementation

### Language Processing Pipeline
1. **Lexical Analysis**: Source code → Tokens
2. **Syntax Analysis**: Tokens → Abstract Syntax Tree
3. **Semantic Analysis**: AST validation and error checking
4. **Interpretation**: AST execution with variable management

### WebSocket Protocol
Interactive execution uses JSON message protocol:
```json
// Input request
{"type": "input_request", "message": "? ", "variable": "a"}

// User input
{"type": "input", "value": "42"}

// Program output
{"type": "output", "data": "42"}

// Execution complete
{"type": "execution_finished", "success": true}
```

### Error Handling
- Lexical errors: Invalid characters, malformed tokens
- Syntax errors: Invalid grammar, missing tokens
- Semantic errors: Undefined line numbers in GOTO statements
- Runtime errors: Division by zero, invalid input types

## Project Structure

```
simple-language-ide/
├── main.py              # FastAPI application and WebSocket handlers
├── lexer.py             # Tokenization logic
├── parser.py            # Grammar parsing and semantic analysis
├── interpreter.py       # Code execution engine
├── meu_ast.py          # AST node definitions
├── errors.py           # Custom exception classes
├── requirements.txt    # Python dependencies
├── run.py              # Local development server
├── Dockerfile          # Container configuration
├── static/
│   └── index.html      # Web IDE interface
└── README.md           # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Roadmap

- [ ] Enhanced error messages with suggestions
- [ ] Code formatting and auto-indentation
- [ ] Variable watch window
- [ ] Step-by-step debugging
- [ ] File save/load functionality
- [ ] Syntax highlighting improvements
- [ ] Mobile responsive optimizations

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

Built with FastAPI, WebSockets, and modern web technologies. Inspired by classic BASIC interpreters and educational programming environments.