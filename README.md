# Security Toolbox (Python)

Toolbox CLI para executar testes de segurança modulares.

## Como rodar

1. Crie um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

    Execute a partir da raiz do projeto:

    python -m src.main

    No menu, escolha o teste e preencha os inputs solicitados.

Como criar um novo teste

    Em src/tests/ crie meu_teste.py.

    Importe BaseTest e implemente a interface (name, description, requires, run).

    No final do arquivo, exponha uma instância como test = MinhaClasse().

    O main.py descobrirá automaticamente o teste.

Boas práticas

    Mantenha run() idempotente e trate timeouts/exceções.

    Não execute testes intrusivos sem autorização.

    Logue resultados sensíveis com cuidado (não deixar credenciais em logs).


---

# Recomendações práticas e próximos passos (curto e direto)
- Para testes HTTP use `requests` com `Session()` e `Timeout`. Para carga use `concurrent.futures.ThreadPoolExecutor` ou `asyncio + httpx`.
- Para resultados legíveis e relatórios, salve JSON/CSV no diretório `results/` com timestamp.
- Considere adicionar um sistema de permissões/consentimento (ex.: confirmação antes de rodar testes intrusivos).
- Para integração com pipelines/CI, crie uma opção `--headless` no `main.py` (aceita inputs via args/env) para rodar testes automaticamente.
- Adicione testes unitários para cada módulo (`pytest`) e um `pre-commit` com linters.

---

Se quiser, eu já posso:
- Gerar o repositório ZIP com esses arquivos prontos; ou
- Substituir o `intruder` simulado por uma versão que faz requisições reais com threads/async (mostrando exemplo com `concurrent.futures` ou `asyncio + httpx`); ou
- Criar a mesma solução usando `typer`/`click` para uma CLI mais robusta e flags.

Qual desses você prefere que eu entregue agora? (se quiser, já faço direto o cód