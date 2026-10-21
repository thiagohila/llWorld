# llWorld

Protótipo de jogo: um mundo simulado que evolui sozinho, com personagens movidos por LLM. Primeiro recorte: o jogador como **conselheiro do Rei Arthur**, por chat — Arthur decide sozinho; o jogador influencia, não controla.

Princípio: **a simulação manda nas regras do mundo; a LLM propõe decisões de alto nível que o jogo valida e executa.** Nada narrado pode contradizer o estado da simulação.

## Fase atual (2026-10-21)

- **Concluída — o jogo:** o fork roda como veio, com melhorias (HUD e arte nova, −27–33% de custo por dia, poderes com feedback, Smite corrigido, mentes de LLM com controle de custo e fontes grátis — Gemini testado de verdade).
- **Próxima — o projeto:** implementar o `arthur/` (conselheiro do Rei Arthur) e ajustar as camadas/interfaces entre ele e o jogo. Plano por etapas em `docs/roadmap.md`. Etapas 0 (decisões: **tudo no mais simples, tudo no Gemini**) e 1 (esqueleto + chat de ponta a ponta, sem LLM) feitas. Próxima: etapa 2 (reino do Arthur).
- LLM controlável em jogo: botão **AI**/tecla `M`, `/control?action=ai…`, `ai on|off|cap|forget` no terminal. O Arthur deve obedecer o mesmo interruptor e teto.
- Trabalhar em etapas pequenas e testáveis, combinadas com o Thiago antes de começar cada uma. Decisões de produto são dele.

## Camadas

- **`worldbox/`** — fork de `ryfcx/worldbox` (simulador em Python; **não** é o WorldBox – God Simulator comercial), submódulo git (`thiagohila/worldbox`). "O jogo" = sempre este fork. Tratar como terceiros: não editar; se inevitável, mudança mínima e genérica, commitada no submódulo e depois o ponteiro no repo raiz.
- **`arthur/`** — **Arthur**, a parte do Thiago no projeto (o conselheiro do Rei Arthur). Tem **HUD e servidor próprios** (`http://127.0.0.1:8766/`, com o mapa do jogo num frame), no mesmo processo do jogo, lendo o mundo sob `runner.lock`. Usa o jogo só pela superfície pública, sempre via `arthur/arthur/bridge.py` — contrato em `docs/roadmap.md` → Interfaces. Rodar: `python arthur/run.py` (da raiz). O jogo tem um mecanismo genérico de painéis (`LiveServer.add_extension`) que o Arthur não usa.
- **`worldbox-clone-backup/`** — cópia não versionada do fork. Não editar nem commitar.

## Onde está o contexto

| Preciso de… | Ler |
|---|---|
| o que estamos construindo | `llWorld-visao-produto.md` |
| estado atual e próximas etapas | `docs/roadmap.md` |
| índice e convenções dos docs | `docs/README.md` |
| versões (Python, git, fork, modelos LLM, portas) e setup do zero | `docs/ambiente.md` |
| como o jogo funciona, por tema | `docs/worldbox/01..06-*.md` |
| rodar e testar | `docs/worldbox/05-executar-e-testar.md` |
| onde plugar código e problemas conhecidos | `docs/worldbox/06-extensao-e-armadilhas.md` |
| segurança (chaves, servidor local) | `docs/worldbox/07-seguranca.md` |
| o que falta resolver (checklists) | `docs/pendencias/jogo.md`, `docs/pendencias/projeto.md` |
| como a IA do jogo funciona (fontes, custo) | `docs/worldbox/03-ia.md` |
| performance | `docs/worldbox/08-performance.md` |
| ideias (não aprovadas) para a IA do Arthur | `docs/rascunhos/` |

Leia sob demanda; não carregue tudo.

## Agentes do projeto (`.claude/agents/`)

- **`worldbox-guide`** — somente leitura; responde dúvidas sobre o código do jogo e confere se os docs batem com o código.
- **`sim-runner`** — roda o jogo com segurança (headless, determinismo/md5, mapa ao vivo) e relata.

## Essenciais do ambiente

- Python 3.14 na `.venv` da raiz (`source .venv/bin/activate`; recriar com `python3.14 -m venv .venv`). O `python3` global do pyenv (3.8) não funciona.
- Dentro de `worldbox/`: `PYTHONDONTWRITEBYTECODE=1 python -m worldbox.main --no-ai --days 3000 --seed 42`.
- Mapa ao vivo em `http://127.0.0.1:8765/` (não `localhost`: OrbStack usa a porta). Com IA: `python -m worldbox.main --live` (sem `--no-ai`).
- LLM: `worldbox/.env` (gitignored, **nunca ler nem exibir valores**). Hoje configurado com Gemini grátis via `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`; para não estourar o plano grátis, `LLM_MAX_CALLS_PER_MINUTE=5`. Para desenvolver sem rede nem custo: `LLM_BASE_URL=mock`.
- Testes offline (API simulada, sem rede, nunca leem o `.env`): `tests/worldbox/` — rodar conforme `tests/worldbox/README.md`. Regressão da simulação = md5 com mesmo seed (`--no-ai`, sem chaves no ambiente). Medições: `tools/perf/`.

## Regra de remotes do jogo

Mudanças no jogo vão **só para o repo do Thiago** (`origin` = `thiagohila/worldbox`). **Nunca** fazer push, PR, issue ou qualquer envio para o upstream `ryfcx/worldbox` (remote `upstream`), a menos que ele peça explicitamente naquele momento.
Reforçado no git do submódulo: `upstream` tem push URL `DISABLED` (fetch continua funcionando). Não desfazer.

## Convenções

- Comunicação com o usuário e docs em português; código do fork em inglês.
- Docs marcam **[código]** / **[executado]** / **[hipótese]** e citam `arquivo.py:função`.
- Ao atualizar o submódulo, revisar `docs/worldbox/` e o hash de referência em `docs/README.md`.
- Mudou versão de qualquer coisa (Python, fork, modelo, dependência)? Atualizar `docs/ambiente.md`.
