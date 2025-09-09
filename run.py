#!/usr/bin/env python3
"""
Script para iniciar a IDE Simple
"""
import os
import sys
import webbrowser
import time
from threading import Timer

def open_browser():
    """Abre o navegador após um pequeno delay"""
    print("🌐 Abrindo navegador...")
    webbrowser.open('http://localhost:8000')

def main():
    print("🚀 Simple Language IDE")
    print("=" * 50)
    
    # Verificar se os arquivos necessários existem
    required_files = [
        'main.py', 'lexer.py', 'parser.py', 
        'interpreter.py', 'meu_ast.py', 'errors.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Arquivos necessários não encontrados:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nCertifique-se de ter todos os arquivos do projeto na pasta atual.")
        sys.exit(1)
    
    # Verificar se o diretório static existe
    if not os.path.exists('static'):
        print("📁 Criando diretório static...")
        os.makedirs('static')
    
    # Verificar se index.html existe em static
    if not os.path.exists('static/index.html'):
        print("❌ Arquivo static/index.html não encontrado!")
        print("Execute este script no diretório que contém todos os arquivos do projeto.")
        sys.exit(1)
    
    print("✅ Todos os arquivos encontrados!")
    print("🔄 Iniciando servidor FastAPI...")
    
    # Agendar abertura do navegador
    timer = Timer(2.0, open_browser)
    timer.start()
    
    # Executar o servidor
    try:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except ImportError:
        print("❌ uvicorn não encontrado. Instalando dependências...")
        os.system("pip install -r requirements.txt")
        print("✅ Dependências instaladas. Executando novamente...")
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n👋 Servidor interrompido. Até logo!")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")

if __name__ == "__main__":
    main()