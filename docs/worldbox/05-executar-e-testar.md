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

Com IA (fonte configurada em `worldbox/.env`, ver `03-ia.md` → Fontes de LLM):

```bash
python -m worldbox.main --live                                   # mentes ligadas
LLM_MAX_CALLS_PER_MINUTE=5 python -m worldbox.main --live        # teto por minuto sem editar o .env
LLM_BASE_URL=mock python -m worldbox.main --live                 # mentes offline, sem rede nem custo
```

Variáveis do ambiente sobrepõem as do `.env`.

Outras flags de `main.py`: `--seed`, `--days`, `--width`, `--height`, `--population`.

## Testes

- **[executado]** Testes offline em `tests/worldbox/` no repo do llWorld (como rodar: `tests/worldbox/README.md`); scripts de medição em `tools/perf/`. O fork em si não tem suíte.
- Regressão disponível:
  1. `tools/compare_runs.py` — métricas lado a lado entre duas configs.
  2. md5 da saída headless com o mesmo seed, sem chaves no ambiente:
     ```bash
     PYTHONDONTWRITEBYTECODE=1 env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY \
       python -m worldbox.main --no-ai --days 3000 --seed 42 | md5
     ```
     **[executado]** Referência: `46183c8d284315695c7706c0f923745a` (igual em 3.10, 3.12 e 3.14).
- Como os testes de IA offline funcionam (`tests/worldbox/test_ai_*.py`):
  - simular a API trocando `worldbox.ai.minds.chat` (mentes) ou `worldbox.ai.client.urllib.request.urlopen` (cliente e narrador) — nada vai para a rede;
  - **isolar do `.env` real**: `client._DOTENV_LOADED = True` antes de qualquer chamada e limpar `LLM_*`/chaves do ambiente — senão o teste lê a fonte configurada do usuário;
  - motor completo com `LLM_BASE_URL=mock` e `urlopen` trocado por uma função que falha, para provar que não houve rede.
  - Cobertos: backoff em 429, parada em 401, rejeição de `{}`, teto por minuto e por tempo real, chamadas puladas, parâmetros por fonte, reenvio após 400, narrador só com OpenAI, fonte genérica com e sem chave, mente `mock`.

## Determinismo

- **[executado]** Mesmo seed + `--no-ai` + sem chaves → mesma história.
- **[executado]** Com as duas chaves no ambiente, mesmo com `--no-ai`, a história muda (`12e24ca4…`). Rodar a regressão sem chaves exportadas.
- **[código]** Modo `--live` e ferramentas de deus não são determinísticos (dias dependem do relógio de parede).
- **[código]** Com IA ligada, as respostas chegam em dias variáveis: não reprodutível.
