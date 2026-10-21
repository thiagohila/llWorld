# Testes do jogo (fork `worldbox/`)

Testes offline, sem rede e sem gastar API: a LLM é simulada e o `.env` real nunca é lido. Ficam no repo do llWorld (não no fork) e recebem o caminho do fork como argumento.

Rodar da raiz do llWorld:

```bash
export PYTHONDONTWRITEBYTECODE=1
for t in tests/worldbox/test_*.py; do .venv/bin/python -I -B "$t" "$PWD/worldbox" | tail -1; done
```

| Arquivo | Cobre |
|---|---|
| `test_ai_minds.py` | mentes com API simulada: chamadas e políticas, teto por tempo real, backoff em 429, parada em 401, rejeição de `{}`, parâmetros OpenAI e reenvio após 400, narrador só com OpenAI |
| `test_ai_sources.py` | fonte genérica do `.env` (URL, auth, parâmetros), Ollama sem chave, mente `mock` num motor completo sem rede, `LLM_MAX_CALLS_PER_MINUTE` |
| `test_ai_controls.py` | LLM em tempo real: desligar/ligar (sem chamadas, políticas mantidas, narrador recusado, evento), teto por minuto em runtime vs `.env`, esquecer decisões, preferências sobrevivem ao reset |
| `test_extensions.py` | rotas genéricas `/ext` do jogo com uma extensão de eco: token, `Host`, `Origin`, tamanho, repasse de GET/POST, erro sem vazar detalhes |
| `test_smite.py` | Smite mata todos no raio na hora, sem contar como morte em guerra |
| `test_featured.py` | `found_tribe`/`settle_people` (tribo, chefe, acampamento, casas, sem evento), pessoas destacadas no `/state` (posição, cor, rótulo cortado, mortos saem, `unfeature`), botão de fundar do mapa intacto |

Testes do Arthur (`tests/arthur/`) recebem o caminho de `arthur/`: `for t in tests/arthur/test_*.py; do .venv/bin/python -I -B "$t" "$PWD/arthur" | tail -1; done`. `test_server.py` cobre o servidor e o HUD; `test_kingdom.py`, o reino (etapa 2); `test_council.py`, a mente do rei (etapa 3).

Regressão da simulação (não é teste unitário): md5 em `docs/worldbox/05-executar-e-testar.md`.
Medições de performance: `tools/perf/` (benchmarks, profiling, memória, envelhecimento, checagem de PNG).
