# worldbox — executar e testar

## Ambiente

- Python **3.10+**, sem dependências.
- **[executado]** O `python3` do pyenv (3.8.13) quebra ao importar `ssl` (falta OpenSSL 1.1) — não usar. O 3.12 do Homebrew funcionou; 3.10 em instalação.
- Chaves (opcional): `worldbox/.env` a partir de `.env.example`.
- Para não criar `__pycache__` no submódulo ao experimentar: `PYTHONDONTWRITEBYTECODE=1`.

## Comandos (dentro de `worldbox/`)

```bash
python3.10 -m worldbox.main --no-ai --days 3000 --seed 42   # headless, sem rede, imprime resumo
python3.10 -m worldbox.main --live [--no-ai] [--no-open]    # mapa em http://127.0.0.1:8765/
python3.10 -m worldbox.main --view 20000 [--no-open]        # grava e gera worldbox.html
python3.10 -m worldbox.main                                 # REPL
python3.10 tools/compare_runs.py --days 6000                # compara configs em vários seeds
```

Outras flags de `main.py`: `--seed`, `--days`, `--width`, `--height`, `--population`.

## Testes

- **[executado]** Não há suíte automatizada.
- Regressão disponível:
  1. `tools/compare_runs.py` — métricas lado a lado entre duas configs.
  2. md5 da saída headless com o mesmo seed:
     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3.10 -m worldbox.main --no-ai --days 3000 --seed 42 | md5
     ```
     **[executado]** Referência no 3.12, sem chaves no ambiente: `46183c8d284315695c7706c0f923745a`. Confirmar o valor no 3.10.
- Para testes de código que chamam IA: monkeypatch de `worldbox.ai.minds._think` ou `worldbox.ai.client.chat`, sem rede.

## Determinismo

- **[executado]** Mesmo seed + `--no-ai` + sem chaves → mesma história.
- **[executado]** Com as duas chaves no ambiente, mesmo com `--no-ai`, a história muda (`12e24ca4…`). Rodar a regressão sem chaves exportadas.
- **[código]** Modo `--live` e ferramentas de deus não são determinísticos (dias dependem do relógio de parede).
- **[código]** Com IA ligada, as respostas chegam em dias variáveis: não reprodutível.
