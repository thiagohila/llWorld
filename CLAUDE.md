# llWorld

Protótipo de jogo: um mundo simulado que evolui sozinho, com uma LLM no papel de personagem autônomo. O primeiro recorte é o jogador como **conselheiro do Rei Arthur**, por chat. Arthur decide sozinho; o jogador influencia, mas não controla.

- Visão de produto (fonte de verdade sobre o que construir): `llWorld-visao-produto.md`
- Princípio técnico: **a simulação manda nas regras do mundo; a LLM propõe decisões de alto nível que o jogo valida e executa.** Nada narrado pode contradizer o estado da simulação.

## Camadas

- **`worldbox/`** — fork do jogo original, incluído como submódulo git. É o motor e a referência de regras do mundo. Tratar como camada de terceiros: evitar alterá-lo; quando inevitável, mudanças mínimas, isoladas e genéricas (ganchos/seams), commitadas no submódulo.
- **`worldbox-ai/`** — a camada própria do llWorld (ainda não existe). Arthur, conselheiro, chat, memória e decisões de alto nível vivem aqui e falam com o motor só pela superfície pública dele (engine, EventLog, MindDirector, SocialContext, LiveState), sem copiar lógica do fork.

## Layout

```
llWorld/
  CLAUDE.md, README.md, llWorld-visao-produto.md
  worldbox-ai/               (a criar) camada própria
  worldbox/                  submódulo git (fork: thiagohila/worldbox) — o motor
    worldbox/                pacote Python
      config.py              todos os parâmetros; AIConfig controla as mentes
      rules.py               pontuadores de utilidade dos agentes (arquivo feito para editar)
      main.py                CLI: --live, --view, --days, --no-ai, --seed
      world/                 terreno, grid, comida
      agents/                Agent, Memory, decide()/execute(), utilidade
      society/               tribos, assentamentos, tecnologia, diplomacia, guerra, doenças
      simulation/engine.py   SimulationEngine.step() (o dia) + SimulationRunner (thread)
      simulation/events.py   EventLog (ring buffer com subscribe)
      simulation/chronicle.py Chronicle (marcos permanentes)
      ai/client.py           chat() HTTP stdlib; DeepSeek e OpenAI; erros como valor
      ai/minds.py            MindDirector/TribePolicy: LLM decide política por tribo
      ai/inventions.py       invenções propostas pela LLM, validadas por materiais
      ai/narrator.py         narração da crônica
      cli/webview.py         servidor do mapa ao vivo (só GET) + cli/static/live.html
    tools/                   compare_runs.py (regressão), build_viewer.py
  worldbox-clone-backup/     cópia não versionada do submódulo; não editar
```

O README raiz cita `docs/`; ainda não existe. Status atual: ambiente sendo preparado (instalando Python 3.10) para rodar o jogo.

## Executar

Python **3.10+**, sem dependências. O `python3` do pyenv (3.8) não funciona.

```bash
cd worldbox
python3.10 -m worldbox.main --no-ai --days 3000 --seed 42   # headless, determinístico, sem rede
python3.10 -m worldbox.main --live                          # mapa em http://127.0.0.1:8765/
python3.10 -m worldbox.main                                 # REPL: minds, chronicle, tribe <id>, narrate
python3.10 tools/compare_runs.py --days 6000                # comparar métricas entre configs
```

- Chaves: `worldbox/.env` (copiar de `.env.example`) com `DEEPSEEK_API_KEY` e/ou `OPENAI_API_KEY`.
- Use `127.0.0.1`, não `localhost`: o OrbStack ocupa `*:8765` nesta máquina.
- Para não sujar o repo ao experimentar: `PYTHONDONTWRITEBYTECODE=1`.

## Testes

Não há suíte de testes. Regressão hoje = `compare_runs.py` + comparar o md5 da saída de `--no-ai --seed 42 --days 3000` antes e depois (sem chaves no ambiente). Testes novos: `unittest` da stdlib, sem rede (monkeypatch de `worldbox.ai.minds._think` ou `chat`).

## Como a IA se conecta ao motor (padrão a seguir)

1. Contexto montado na thread da simulação, sob `runner.lock` (`_brief_tribe`).
2. Chamada HTTP fora da thread (`ThreadPoolExecutor`).
3. Resposta volta por `queue.Queue` e é aplicada em `MindDirector.tick()` → `_drain()`, dentro do dia.
4. JSON validado e convertido em objeto tipado (`parse_policy`, `validate_proposal`); valores são limitados, nunca aplicados crus.
5. O efeito chega ao mundo por pontos existentes: `SocialContext` (bias de ação), proporções de profissão, `diplomacy.adjust`, pesquisa.

Nunca chamar a LLM de dentro de `step()`/`rules.py` nem mutar `engine.*` a partir de threads de rede. Rotas HTTP com rede devem soltar o lock antes da chamada (ver `LiveState.explain`).

## Armadilhas conhecidas

- Falha de API não atualiza `last_thought` → a tribo tenta de novo todo dia simulado.
- `parse_policy({})` vira política padrão e substitui a anterior.
- `_nudge_diplomacy` aplica a lista `toward` todo dia (um "war" ≈ −128 de relação em 40 dias).
- Narrador só funciona com `DEEPSEEK_API_KEY` (o `narrate` checa apenas essa chave).
- Determinismo: com as duas chaves no ambiente, `--no-ai` muda a história do mesmo seed (`engine.py`, herança de `ai_house` sorteia `rng`).
- O chefe da tribo é reeleito todo dia por prestígio (`culture.choose_chieftain`); um líder fixo (Arthur) exigirá mudança.
- Memória do agente é rasa (`Memory.log` com 8 entradas); não há relações entre indivíduos.
- `register_technology` é global; só é limpo em `engine.reset()`.

## Convenções

- Código do motor em inglês, estilo do upstream: docstrings explicando o porquê, stdlib apenas, `@dataclass`, erros como valores na camada de IA.
- Funcionalidade nova vai em `worldbox-ai/`. Mudanças no motor só quando não houver ponto de extensão; acontecem no submódulo `worldbox/` (commit lá, depois atualizar o ponteiro no repo raiz).
- Comunicação com o usuário em português.
