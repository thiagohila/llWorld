# Pendências — jogo (fork `worldbox/`)

Problemas e limitações encontrados no fork. Corrigir aqui significa **editar o fork** (commit no submódulo) ou contornar pelo `worldbox-ai/` — decidir caso a caso.

Formato: `- [ ] **título** — detalhe. Onde. Ref.` · Prioridade: 🔴 alta · 🟡 média · ⚪ baixa. Ao resolver, marque `[x]` e anote commit/data.

## Segurança

- [ ] 🔴 **CSRF nas rotas que alteram estado** — `/act`, `/found`, `/control`, `/explain` são GET sem token nem checagem de `Origin`; qualquer site aberto no navegador dispara ações (e gasta API se houver chave). `cli/webview.py:_handler_factory`. Ref.: `docs/worldbox/07-seguranca.md`.
- [ ] 🔴 **DNS rebinding** — `Host` não é validado; um site externo pode ler `/state`. `cli/webview.py`. Ref.: `07-seguranca.md`.
- [ ] 🟡 **`radius` sem limite em `/act`** — valor enorme congela a simulação segurando o lock. `cli/webview.py:LiveState.act`, `world/world.py:tiles_within`.
- [ ] ⚪ **Erro 500 devolve texto da exceção** — `send_error(500, str(error))`. `cli/webview.py`.
- [ ] ⚪ **`load_dotenv` sobe a árvore de diretórios** — pode carregar um `.env` alheio em `~/Documents` ou `~`. `ai/client.py:load_dotenv`.
- [ ] ⚪ **Erro da API repassado com até 300 caracteres** — exibido no painel Minds; checar se algum provedor ecoa a chave. `ai/client.py:chat`.

## IA (mentes das tribos)

- [ ] 🔴 **Falha de API repete todo dia** — `_drain` não atualiza `last_thought` em erro; com chave inválida cada tribo chama a API a cada dia simulado. `ai/minds.py:MindDirector._drain`/`_schedule`.
- [ ] 🟡 **`parse_policy({})` substitui a política** — JSON vazio vira política padrão em silêncio. `ai/minds.py:parse_policy`.
- [ ] 🟡 **`tribe_id` inválido passa no parse** — só é ignorado na aplicação. `ai/minds.py:parse_policy`, `_nudge_diplomacy`.
- [ ] 🟡 **Narrador só funciona com DeepSeek** — `narrate` checa só `DEEPSEEK_API_KEY`; com apenas OpenAI, "No API key". `ai/narrator.py:narrate`.
- [ ] ⚪ **`errors` alterado sem lock** — `_drain` escreve em `self.errors` fora de `_lock`, enquanto `snapshot` lê com lock. `ai/minds.py`.

## Determinismo e testes

- [ ] 🟡 **Chaves no ambiente mudam a história mesmo com `--no-ai`** — `_spawn_founder` atribui `ai_house` sempre; `_process_births` só sorteia `rng` quando os pais têm casas diferentes. `simulation/engine.py`. Ref.: `docs/worldbox/05-executar-e-testar.md`.
- [ ] 🟡 **Sem suíte de testes** — só `tools/compare_runs.py` e md5 manual.
- [ ] ⚪ **Registro global de tecnologias** — `register_technology` só limpa em `engine.reset()`; atrapalha vários motores no mesmo processo. `society/technology.py`.

## Limitações relevantes para o protótipo do Arthur

Não são bugs do jogo; são lacunas para o que queremos construir. Ref.: `docs/worldbox/06-extensao-e-armadilhas.md`.

- [ ] 🔴 **Chefe reescolhido todo dia** — não existe líder fixo. `society/culture.py:choose_chieftain`, `simulation/engine.py:_process_roles_and_leadership`. Contornável por fora (patch) ou gancho no fork.
- [ ] 🟡 **Memória do agente com 8 entradas e sem relações individuais** — `agents/agent.py:Memory`.
- [ ] 🟡 **`toward` aplicado todo dia** — um "war" ≈ −128 de relação em 40 dias; magnitude é parâmetro de gameplay. `ai/minds.py:_nudge_diplomacy`.
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
- [ ] ⚪ **Eventos `SYSTEM` fora do feed do servidor** — quem consumir `/state` (ex.: `worldbox-ai`) não vê o uso de poderes. Avaliar incluir `system` em `LOGGED_KINDS`.

## Divergências de documentação do fork

- [ ] ⚪ **README do fork diz que a IA fica "ao lado" do motor** — `engine.py` importa `ai.minds`/`ai.inventions` diretamente.
