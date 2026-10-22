# Pendências — jogo (fork `worldbox/`)

Estado em 2026-10-21 (fork em `bbbea3a`): o jogo funciona; o que segue são riscos, limitações e lacunas para a próxima fase. Problemas e limitações encontrados no fork. Corrigir aqui significa **editar o fork** (commit no submódulo) ou contornar pelo `arthur/` — decidir caso a caso.

Formato: `- [ ] **título** — detalhe. Onde. Ref.` · Prioridade: 🔴 alta · 🟡 média · ⚪ baixa. Ao resolver, marque `[x]` e anote commit/data.

## Segurança

- [ ] 🔴 **CSRF nas rotas que alteram estado** — `/act`, `/found`, `/control`, `/explain` são GET sem token nem checagem de `Origin`; qualquer site aberto no navegador dispara ações (e gasta API se houver chave). `cli/webview.py:_handler_factory`. Ref.: `docs/worldbox/07-seguranca.md`.
- [ ] 🔴 **DNS rebinding** — `Host` não é validado; um site externo pode ler `/state`. `cli/webview.py`. Ref.: `07-seguranca.md`.
- [ ] 🟡 **`radius` sem limite em `/act`** — valor enorme congela a simulação segurando o lock. `cli/webview.py:LiveState.act`, `world/world.py:tiles_within`.
- [ ] ⚪ **Erro 500 devolve texto da exceção** — `send_error(500, str(error))`. `cli/webview.py`.
- [ ] ⚪ **`load_dotenv` sobe a árvore de diretórios** — pode carregar um `.env` alheio em `~/Documents` ou `~`. `ai/client.py:load_dotenv`.
- [ ] ⚪ **Erro da API repassado com até 300 caracteres** — exibido no painel Minds; checar se algum provedor ecoa a chave. `ai/client.py:chat`.

## IA (mentes das tribos)

- [x] 🔴 **Falha de API repete todo dia** — backoff exponencial por tribo (dias simulados e tempo real); 401/403/404 param todas as mentes até o reset. commit `d6472e1`.
- [x] 🟡 **`parse_policy({})` substitui a política** — JSON vazio agora é rejeitado em `MindDirector._drain` e conta como falha. commit `d6472e1`.
- [ ] 🟡 **`tribe_id` inválido passa no parse** — só é ignorado na aplicação. `ai/minds.py:parse_policy`, `_nudge_diplomacy`.
- [x] 🟡 **Narrador só funciona com DeepSeek** — `narrate` aceita qualquer chave e `chat()` cai no provedor disponível. commit `d6472e1`.
- [ ] 🟡 **Observar: mais guerras com IA ligada?** — com o controle de custo, uma política dura mais tempo de jogo e `_nudge_diplomacy` a aplica todo dia; medir guerras com e sem IA antes de mexer.
- [ ] ⚪ **Parâmetros do `gpt-5-mini` não confirmados** — o cliente se adapta a um 400, mas só uma chamada real com chave OpenAI confirma. `ai/client.py:chat`.
- [ ] ⚪ **`errors` alterado sem lock** — `_drain` escreve em `self.errors` fora de `_lock`, enquanto `snapshot` lê com lock. `ai/minds.py`.

## Determinismo e testes

- [ ] 🟡 **Chaves no ambiente mudam a história mesmo com `--no-ai`** — `_spawn_founder` atribui `ai_house` sempre; `_process_births` só sorteia `rng` quando os pais têm casas diferentes. `simulation/engine.py`. Ref.: `docs/worldbox/05-executar-e-testar.md`.
- [ ] 🟡 **Sem suíte de testes no fork** — mitigado: testes offline do jogo vivem no llWorld (`tests/worldbox/`: mentes, fontes de LLM, Smite) + md5 + `tools/compare_runs.py`. Falta cobrir simulação (combate, doenças, assentamentos) e rodar tudo num comando.
- [ ] ⚪ **Registro global de tecnologias** — `register_technology` só limpa em `engine.reset()`; atrapalha vários motores no mesmo processo. `society/technology.py`.

## Limitações relevantes para o protótipo do Arthur

Não são bugs do jogo; são lacunas para o que queremos construir. Ref.: `docs/worldbox/06-extensao-e-armadilhas.md`.

- [ ] 🔴 **Chefe reescolhido todo dia** — não existe líder fixo. `society/culture.py:choose_chieftain`, `simulation/engine.py:_process_roles_and_leadership`. Contornável por fora (patch) ou gancho no fork.
- [ ] 🟡 **Memória do agente com 8 entradas e sem relações individuais** — `agents/agent.py:Memory`.
- [ ] 🟡 **`toward` aplicado todo dia** — um "war" ≈ −128 de relação em 40 dias; magnitude é parâmetro de gameplay. `ai/minds.py:_nudge_diplomacy`.
- [x] 🟡 **Fundar civilização só existe dentro do servidor** — extraída para `society/founding.py` (`found_tribe`, `settle_people`); `LiveState.found_civ` usa e dá o mesmo resultado com a mesma seed (comparado antes/depois). 2026-10-21.
- [ ] ⚪ **Ações sem suporte no motor** — emissários, espionagem, investigação de intenções não existem.
- [ ] ⚪ **Fork não é instalável** — sem `pyproject`; código externo precisa de `sys.path`/`PYTHONPATH`.

## Performance

Ref.: `docs/worldbox/08-performance.md`.

- [x] 🟡 **Velocidades não são taxas** — runner agora usa período-alvo; HUD mostra dias/s reais. commit `bfe84cd`.
- [x] 🟡 **`find_enemy` caro** — `enemies_map` por fase; md5 idêntico. commit `bfe84cd`.
- [x] ⚪ **Enum como chave no caminho quente** — `Goal`/`TerrainType` com hash de identidade; `score_actions`/`choose` enxutos. commit `bfe84cd`.
- [x] ⚪ **Front-end reconstrói listas a cada poll** — só quando mudam; cache de sprite com chave curta. commit `b10f9fb`.
- [ ] ⚪ **Custo por dia ainda cresce com a população** — o que sobra é a pontuação de ações e o movimento por agente (`utility.score_actions`, `build_situation`, `behavior.execute`). Próximo passo, se precisar: profiling com 800+ pessoas.

## Interface

- [x] 🟡 **Poderes sem feedback** — `/act` funcionava, mas os eventos são `EventKind.SYSTEM`, que não entra em `LOGGED_KINDS` (`cli/webview.py`), e Bless/Blight só aparecem nas camadas Farm/Food. Resolvido no front-end (`static/live.html`): efeito visual, toast com o resultado e filtro "Powers" no log. commit `b10f9fb`.
- [x] 🔴 **Smite não matava ninguém** — zerava a saúde, mas a regeneração do dia seguinte roda antes da checagem de morte (0/14 morreram no teste); e marcava ferimento, o que contaria as mortes como guerra. Agora mata na hora com a contabilidade do motor (14/14, `total_war_deaths` intacto). `cli/webview.py:LiveState.act`. commit `d6472e1`.
- [ ] ⚪ **Eventos `SYSTEM` fora do feed do servidor** — quem consumir `/state` (ex.: Arthur) não vê o uso de poderes. Avaliar incluir `system` em `LOGGED_KINDS`.

## Divergências de documentação do fork

- [ ] ⚪ **README do fork diz que a IA fica "ao lado" do motor** — `engine.py` importa `ai.minds`/`ai.inventions` diretamente.
