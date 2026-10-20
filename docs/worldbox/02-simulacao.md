# worldbox — simulação

## Agentes — `agents/`

- **[código]** Decisão por utilidade: `behavior.py:decide()` → `utility.py:choose()` pontua cada `Goal` de 0 a 1 com os pontuadores e `WEIGHTS` de `rules.py`; vence o maior. A escada antiga fica em `decide_by_rules` (alternada por `UtilityConfig.enabled`).
- **[código]** Fatores externos chegam por `behavior.py:SocialContext` (ameaça, casa, multiplicadores `fight_bias`/`flee_bias`/`food_bias`/`mate_bias`, coesão, raio de território). É por aí que as mentes de IA influenciam indivíduos.
- **[código]** Personalidade: `aggression`, `caution`, `industry`, herdados com variação.
- **[código]** `Memory`: locais de comida, terrenos conhecidos e `log` com só 8 entradas. Não há relações entre indivíduos.
- **[código]** Saúde tem teto que cai com a idade (após ~45 anos), não dreno diário.

## Tribos — `society/groups.py`

- **[código]** `GroupRegistry.try_form_or_join`: tribos surgem por encontro. Dividem-se ao crescer (`try_split`, `GroupConfig.split_size`) e se dissolvem quando pequenas (`find_unviable`).
- **[código]** Chefe reescolhido todo dia por prestígio = idade + 3×filhos + 2×abates (`culture.py:choose_chieftain`); puxa a agressividade dos membros (`apply_chieftain_influence`).
- **[código]** Profissões redistribuídas todo dia (`roles.py:assign_roles`), por proporções de `RoleConfig` ou da política da mente.

## Assentamentos, tecnologia, cultura

- **[código]** `settlements.py`: tribo grande funda assentamento; agricultores enchem o celeiro; nível sobe com população + tecnologia (`LEVEL_SPECS`).
- **[código]** `technology.py`: árvore fixa (`TECH_TREE`) por eras; pontos de pesquisa por população e fome. `register_technology` aceita técnicas novas (usado pelas invenções da IA) num **registro global**.
- **[código]** `culture.py`: difusão de conhecimento e troca de comida entre tribos amigas.

## Conflito e doença

- **[código]** `diplomacy.py:Diplomacy.update`: relações derivam para neutro, pioram com proximidade e escassez; guerra abaixo de `war_threshold`, paz por relação ou exaustão (`_should_end`).
- **[código]** `combat.py`: confrontos entre tribos hostis no mesmo espaço.
- **[código]** `epidemics.py`: doenças (`DISEASES`: fever, flux, pox, plague, coughing) espalham por vizinhança; sobreviventes ficam imunes.

## Eventos e história

- **[código]** `events.py:EventLog`: ring buffer (`SimulationConfig.event_log_size`) com `subscribe(listener)`; tipos em `EventKind` (inclui `MIND` para decisões de IA).
- **[código]** `chronicle.py:Chronicle`: só marcos (`Milestone`: era, primeira tecnologia, assentamento, população, guerra, praga, tribo, colapso), guardados para sempre. É a fonte do narrador.
