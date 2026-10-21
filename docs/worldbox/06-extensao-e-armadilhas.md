# worldbox — pontos de extensão e armadilhas

## Pontos de extensão sem editar o fork

| Superfície | Uso | Status |
|---|---|---|
| `engine.events.subscribe(fn)` | observar tudo que acontece | **[código]** |
| `engine.minds` | atributo público; o motor só chama `tick`, `reset`, `policy_for`, `thinking_count`; as interfaces chamam `snapshot` e `policy_for`. Uma subclasse de `MindDirector` atribuída após criar o motor substitui o comportamento | **[código]** |
| `ai.minds.parse_policy`, `TribePolicy` | validar e representar decisões no formato que o motor aplica | **[código]** |
| `agents.behavior.SocialContext` | multiplicadores por agente | **[código]** |
| `society.culture.choose_chieftain` | chamado via módulo pelo motor; pode ser envolvido de fora (patch global no processo) | **[código]** |
| `ai.client.chat` | cliente LLM reutilizável | **[código]** |
| Servidor HTTP próprio no mesmo processo, outra porta, usando `runner.lock` | novas rotas sem tocar `webview.py` | **[hipótese]** |
| `rules.py` (`WEIGHTS`, `@scorer`) | mudar comportamento base — **é edição do fork** | **[código]** |

Padrão para qualquer código com LLM: snapshot sob `runner.lock` → chamada fora do lock/thread → resultado aplicado dentro do `tick`. Nunca chamar LLM dentro de `step()` nem mutar `engine.*` a partir de thread de rede.

**[código]** O fork não é instalável (sem `pyproject`); código externo precisa pôr `worldbox/` no `sys.path` ou `PYTHONPATH`.

## Armadilhas conhecidas

- ~~Falha de API repete todo dia~~ — corrigido: backoff por tribo e parada geral em 401/403/404 (ver `03-ia.md`, Controle de custo).
- ~~`parse_policy({})` vira política padrão~~ — corrigido: `_drain` rejeita política vazia.
- **[código]** `_nudge_diplomacy` aplica `toward` todo dia: decisões de guerra/paz acumulam rápido.
- ~~Narrador só funciona com `DEEPSEEK_API_KEY`~~ — corrigido: aceita qualquer chave.
- **[executado]** Vazamento de determinismo: `_spawn_founder` atribui `ai_house` mesmo com `--no-ai`; em `_process_births` o `rng.random()` só é sorteado se os pais têm casas diferentes (só acontece com as duas chaves).
- **[código]** Chefe reescolhido todo dia: não há líder fixo.
- **[código]** Memória do agente com 8 entradas; nenhuma relação entre indivíduos.
- **[código]** `register_technology` é global; só limpo em `engine.reset()`. Cuidado com vários motores no mesmo processo.
- **[código]** Rotas que alteram estado no mapa ao vivo são GET.
- **[executado]** Porta 8765 compartilhada com o OrbStack nesta máquina; usar `127.0.0.1`.
