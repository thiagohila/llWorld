# worldbox — performance

Medições de 2026-10-20, Python 3.14.6, macOS x86_64, `--no-ai`, seed 42. Script de profiling fica fora do repo (scratchpad).

## Resumo

O gargalo é o **motor em Python**, não o navegador. O custo de um dia cresce com a população, e as velocidades da interface não são taxas fixas: elas somam uma pausa ao tempo do dia.

## Motor — custo por dia simulado

**[executado]** 20.000 dias em 560 s (média 36 dias/s):

| População | ms/dia (média) | p95 | máx |
|---|---|---|---|
| 100–199 | 10,5 | 14,6 | 65 |
| 200–299 | 16,1 | 24,5 | 240 |
| 300–399 | 28,7 | 48,5 | 333 |
| 400–499 | 28,6 | 39,3 | 103 |
| 500–599 | 33,7 | 42,5 | 216 |
| 600–699 | 45,2 | 69,0 | 264 |
| 700–799 | 51,1 | 73,9 | 458 |

Cresce de forma aproximadamente linear (~6–7 ms a cada 100 pessoas), com picos ocasionais de centenas de ms.

**[executado]** Profiling de 300 dias com 603 pessoas (tempo acumulado):

| Função | % do `step` | Observação |
|---|---|---|
| `agents/utility.py:score_actions` (via `decide`/`choose`) | ~28% | roda para cada agente todo dia |
| `society/combat.py:find_enemy` | ~18% | chamada 2× por agente por dia, **em momentos diferentes**: antes do movimento (`_social_context`) e depois (`engagements`, com ocupação reindexada) — não dá para reaproveitar o resultado |
| `agents/behavior.py:execute` | ~17% | movimento, `_wander_or_return_home` |
| `engine._social_context` | ~17% | inclui um dos `find_enemy` |
| `enum.__hash__` | ~5% | 3,8 M chamadas: `Goal` usado como chave de dict no caminho quente |
| `world.tiles_within` / `neighbours` | ~4–7% | geradores chamados milhões de vezes |

## Servidor ao vivo

- **[código]** `SimulationRunner._loop` faz `step()` e depois dorme `delay`. Período real = tempo do dia + delay. Em `Max` (delay 0) roda lotes de dias por aquisição do lock.
- **[executado]** Com 872 pessoas, na velocidade "1×" (delay 0,06 s, teto teórico 16,7 dias/s): **7,1 dias/s reais**. Com população alta, 1×, 4× e Max convergem, porque o tempo do dia domina.
- **[executado]** `/state`: 34 KB por poll, mediana 16 ms (máx 62) segurando o lock — ~3% do tempo da simulação com poll a cada 500 ms. `/overlay` 14 KB/4 ms, `/inspect` <1 KB/1 ms.

## Navegador (HUD novo)

- **[executado]** 919 pessoas, tela 1920×873: render mediana 18,7 ms (p90 20,3); processamento de cada poll 12–27 ms a cada 500 ms (~3–5% da thread); heap ~6 MB; nenhuma long task em 12 s de uso normal.
- Folga existe, mas há gordura: chave de cache do sprite monta `JSON.stringify(pal)` por pessoa a cada quadro, e as listas do painel são reconstruídas a cada poll mesmo sem mudança.

## Otimizações aplicadas (2026-10-20, commits `b10f9fb` e `bfe84cd` no fork)

Todas preservam a simulação: md5 de regressão `46183c8d…` e impressão digital do estado no dia 9500 idênticos antes e depois.

| # | Mudança | Onde |
|---|---|---|
| 1 | `Diplomacy.enemies_map()` montado uma vez por fase; `find_enemy(enemies=...)` retorna na hora para tribos sem inimigos e não chama `are_hostile` por par | `society/diplomacy.py`, `society/combat.py`, `simulation/engine.py` |
| 2 | `Goal` e `TerrainType` com hash de identidade (`__hash__ = object.__hash__`); `score_actions` sem dict de bias por agente e usando `_value_`; `choose` sem reconstruir a lista de chaves por comparação | `agents/behavior.py`, `world/terrain.py`, `agents/utility.py` |
| 4 | Runner com período-alvo: dorme `max(delay − tempo_do_dia, min_tick_sleep)` | `simulation/engine.py:SimulationRunner._loop` |
| 5 | HUD mostra dias/s reais | `cli/static/live.html` |
| 6 | Listas do painel só reconstroem quando os dados mudam; cache de sprite com chave curta | `cli/static/live.html` |

Não aplicada: **3 (índice espacial)** — depois da #1, `find_enemy` saiu do top 18 do profiling; o ganho não justificaria o código.

**[executado]** Resultado no motor:

| Janela | Antes | Depois | Ganho |
|---|---|---|---|
| dias 0–3000 (pop ~248) | 10,05 ms/dia | 7,37 ms/dia | −27% |
| dias 8000–9500 (pop ~455) | 23,03 ms/dia | 15,51 ms/dia | −33% |

**[executado]** Velocidade real no modo ao vivo (pop ~135–200):

| Botão | Alvo | Medido |
|---|---|---|
| ½× | 4 dias/s | 4,0 |
| 1× | 16,7 | 15,0 |
| 4× | 100 | 87,2 |
| Max | sem teto | 135,5 |

Com população alta, as velocidades voltam a convergir quando o próprio dia passa do alvo (ex.: 4× = 10 ms/dia), mas agora 1× só degrada quando um dia custar mais de 60 ms.

## Execução longa: memória, crash, envelhecimento (2026-10-21)

- **[executado]** Servidor ao vivo por 12h45min (motor otimizado): sem crash nem traceback, RSS 18 MB no dia 18.305 com 770 pessoas. O Mac dormiu de 00:41 a 07:17 e o processo parou junto — por isso poucos dias na madrugada. Para rodar a noite: `caffeinate -i`.
- **[executado]** Headless, seed 7, 25.000 dias com `tracemalloc`: heap Python 0,7 → 2,2 MB acompanhando a população (190 → 474), estabilizando junto. Tribos/assentamentos mortos são removidos; só crônica (222) e histórico de guerras (48) crescem — esperado e pequeno. **Sem vazamento.**
- **[executado]** Mesmo seed sem `tracemalloc`, custo por 100 pessoas por janela de 5.000 dias: 4,78 → 4,92 → 5,20 → 5,22 → 5,75 ms. Leve alta (+20% em 25 mil dias), sem termo que varra o histórico no profiling — vem de mais assentamentos, terra cultivada e movimento. Não é vazamento de tempo.
- **[executado]** Front-end: dois crescimentos sem limite corrigidos em `live.html` — mapa anti-repetição de toasts (agora expira em 8 s) e caches de sprite/retrato (podados por tamanho: 4.000 / 600). Aba recarregada: heap ~2 MB, DOM ~1,7 mil nós, log limitado a 300, dias/s do HUD idêntico ao medido no servidor.
- **[executado]** Com ~770 pessoas, `/state` responde em 48–88 ms (pico ~200 ms) porque espera o lock do dia em andamento. Próximo ponto se a população crescer muito.

## Melhorias possíveis (restantes)

Motor (edição do fork; manter o md5 de regressão idêntico):
1. Tornar `find_enemy` mais barato sem mudar o resultado: pular de cara agentes cuja tribo não tem nenhum inimigo hoje (conjunto calculado uma vez por dia) e memorizar `are_hostile` por par no dia. (Reaproveitar a chamada anterior **não** serve — ver tabela.)
2. Tirar trabalho repetido de `score_actions`: `import` dentro da função a cada chamada, dict de bias recriado por agente, `Goal` (Enum) como chave.
3. Índice espacial de inimigos por tile em vez de varrer `tiles_within` por agente.
4. Runner com período-alvo: dormir `max(0, delay − tempo_do_dia)`, para as velocidades significarem dias/s.

Front-end:
5. Mostrar dias/s reais no HUD.
6. Só reconstruir listas do painel quando os dados mudarem; chave de sprite mais barata.
