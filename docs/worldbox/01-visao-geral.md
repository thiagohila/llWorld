# worldbox — visão geral

## Origem

- **[executado]** Upstream: `https://github.com/ryfcx/worldbox` (autores `ryfcx`/Ryan, 7 commits entre 2026-08-10 e 2026-10-07, versão `0.1.0` em `worldbox/__init__.py`). Nosso fork `thiagohila/worldbox` partiu do commit `4579b3c` do upstream (conferido com `git ls-remote` em 2026-10-20) e hoje tem 5 commits próprios: `b10f9fb` (HUD e sprites), `bfe84cd` (performance), `6804118` (arte desenhada), `d6472e1` (fontes de LLM, custo, Smite) e `6dc41f1` (README).
- **Não é o WorldBox – God Simulator** (jogo comercial do Maxim Karpenko, código fechado, versões 0.5x em 2026). Só compartilha o nome e a ideia de "mundo que evolui"; nenhum código, regra ou asset vem de lá. Diferenças em relação ao WorldBox comercial são esperadas em tudo.

## O que é

Simulador de civilizações em Python puro (stdlib, 3.10+). ~100 pessoas num mapa procedural; tribos, assentamentos, tecnologia, guerras e pragas emergem. Tribos grandes podem ser "jogadas" por LLMs — DeepSeek, OpenAI ou qualquer endpoint compatível com OpenAI (inclusive grátis e local), ou por uma mente offline de regras (`mock`). Ver `03-ia.md`.

## Mapa de módulos

```
worldbox/worldbox/
  config.py           todos os parâmetros (dataclasses frozen, uma por sistema, cada uma com `enabled`)
  rules.py            pontuadores de utilidade dos agentes — feito para ser editado
  main.py             CLI e modos de execução
  world/              terreno (water/grass/forest/mountain), grid, camada de comida
  agents/             Agent, Memory, necessidades, decide()/execute(), utilidade, nomes
  society/            tribos, assentamentos, tecnologia, profissões, cultura, diplomacia, combate, doenças
  simulation/         engine (ciclo do dia + runner), eventos, crônica, relógio
  ai/                 cliente LLM (fontes por .env), mentes das tribos, invenções, narrador, mock.py (mente offline)
  cli/                terminal, dashboard, servidor do mapa ao vivo
  cli/static/         live.html (HUD) + sprites/ (spritesheets e sprites.json)
  export.py           grava uma execução em JSON para o viewer
worldbox/tools/       compare_runs.py, build_viewer.py, viewer_template.html
```

**[código]** O README do fork diz que as dependências seguem `cli → simulation → society → agents → world → config` e que a IA fica "ao lado". Na prática `simulation/engine.py` importa `ai.minds` e `ai.inventions`, e `ai/minds.py` lê internos do motor.

## Ciclo de um dia — `simulation/engine.py:SimulationEngine.step()`

1. Comida regenera; tribos recontadas (`groups.refresh`)
2. Necessidades sobem (`apply_daily_upkeep`)
3. Cada agente escolhe um objetivo (`decide`)
4. Cada agente age (`execute`)
5. Refeições contra o chão e o celeiro (`_process_meals`)
6. Combate (`_process_combat`)
7. Doenças (`_process_disease`)
8. Mortes, depois nascimentos
9. Sociedade (`_process_society`): tribos, profissões, chefes, assentamentos, pesquisa, cultura, **mentes de IA** (`minds.tick`), diplomacia
10. Marcos na crônica (`_record_milestones`)
11. Relógio avança

Execução contínua: `SimulationRunner` roda `step()` numa thread segurando `runner.lock` (RLock). Toda leitura externa usa esse lock.

## Glossário

| Termo | Significado | Onde |
|---|---|---|
| agent | uma pessoa | `agents/agent.py:Agent` |
| goal | ação do dia: eat, seek_food, rest, fight, flee, seek_mate, wander | `agents/behavior.py:Goal` |
| group / tribe | tribo; tem conhecimento, chefe, assentamento | `society/groups.py:Group` |
| chieftain | chefe da tribo, reescolhido todo dia por prestígio | `society/culture.py:choose_chieftain` |
| role | profissão: child, forager, farmer, warrior, scholar, healer, elder | `society/roles.py:Role` |
| settlement | assentamento: Camp → Hamlet → Village → Town → City | `society/settlements.py` |
| era | Stone, Agricultural, Bronze, Iron Age | `society/technology.py:ERAS` |
| relation | relação entre duas tribos, −100..100 | `society/diplomacy.py:Diplomacy` |
| event | acontecimento do dia (ring buffer) | `simulation/events.py:EventLog` |
| chronicle | marcos permanentes da história | `simulation/chronicle.py:Chronicle` |
| mind | LLM que decide a política de uma tribo | `ai/minds.py:MindDirector` |
| policy / stance | decisão da mente; stance ∈ survive, farm, expand, defend, research, raid, trade | `ai/minds.py:TribePolicy` |
| house | fonte de LLM atribuída a tribo e pessoa: `deepseek`, `openai`, `custom` (do `.env`) ou `mock` | `ai/client.py:HOUSES`, `all_houses` |
| god tools / powers | intervenções manuais pelo mapa ao vivo: spawn, bless, blight, smite, plague, heal | `cli/webview.py:LiveState.act` |
