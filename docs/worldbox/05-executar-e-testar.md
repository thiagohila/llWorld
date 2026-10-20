# worldbox — executar e testar

## Ambiente

Versões completas e montagem do zero: `../ambiente.md`.

- Python do projeto: **3.14** (Homebrew), numa `.venv` na raiz do llWorld, compartilhada pelo jogo e pelo futuro `worldbox-ai`. O jogo exige 3.10+ e não tem dependências.
- **[executado]** Testado em 3.10.15, 3.12.15 e 3.14.6: mesmo resultado (md5 abaixo). O 3.14 foi o mais rápido (~30 s para 3000 dias, contra ~57 s no 3.10) e roda sem `DeprecationWarning`.
- **[executado]** O `python3` global do pyenv é 3.8.13 e quebra ao importar `ssl` (falta OpenSSL 1.1) — não usar. A `.venv` contorna isso.

Criar ou recriar o ambiente (na raiz do llWorld):

```bash
python3.14 -m venv .venv
source .venv/bin/activate        # depois disso, `python` = 3.14 da venv
```

- Chaves (opcional): `worldbox/.env` a partir de `worldbox/.env.example`.
- Para não criar `__pycache__` no submódulo ao experimentar: `export PYTHONDONTWRITEBYTECODE=1`.

## Comandos (dentro de `worldbox/`, com a venv ativa)

```bash
python -m worldbox.main --no-ai --days 3000 --seed 42   # headless, sem rede, imprime resumo
python -m worldbox.main --live [--no-ai] [--no-open]    # mapa em http://127.0.0.1:8765/
python -m worldbox.main --view 20000 [--no-open]        # grava e gera worldbox.html
python -m worldbox.main                                 # REPL
python tools/compare_runs.py --days 6000                # compara configs em vários seeds
```

Sem ativar a venv: troque `python` por `../.venv/bin/python`.

Outras flags de `main.py`: `--seed`, `--days`, `--width`, `--height`, `--population`.

## Testes

- **[executado]** Não há suíte automatizada.
- Regressão disponível:
  1. `tools/compare_runs.py` — métricas lado a lado entre duas configs.
  2. md5 da saída headless com o mesmo seed, sem chaves no ambiente:
     ```bash
     PYTHONDONTWRITEBYTECODE=1 env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY \
       python -m worldbox.main --no-ai --days 3000 --seed 42 | md5
     ```
     **[executado]** Referência: `46183c8d284315695c7706c0f923745a` (igual em 3.10, 3.12 e 3.14).
- Para testes de código que chamam IA: monkeypatch de `worldbox.ai.minds._think` ou `worldbox.ai.client.chat`, sem rede.

## Determinismo

- **[executado]** Mesmo seed + `--no-ai` + sem chaves → mesma história.
- **[executado]** Com as duas chaves no ambiente, mesmo com `--no-ai`, a história muda (`12e24ca4…`). Rodar a regressão sem chaves exportadas.
- **[código]** Modo `--live` e ferramentas de deus não são determinísticos (dias dependem do relógio de parede).
- **[código]** Com IA ligada, as respostas chegam em dias variáveis: não reprodutível.
