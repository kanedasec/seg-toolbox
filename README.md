# Security Toolbox (Python)

Toolbox CLI para executar testes de segurança modulares.

## Como rodar

1. Crie um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Execute a partir da raiz do projeto:
    ```bash
    python -m src.main

No menu, escolha o teste e preencha os inputs solicitados.

## Como criar um novo teste

Em src/tests/ crie meu_teste.py.

Importe BaseTest e implemente a interface (name, description, requires, run).

No final do arquivo, exponha uma instância como test = MinhaClasse().

O main.py descobrirá automaticamente o teste.

---
