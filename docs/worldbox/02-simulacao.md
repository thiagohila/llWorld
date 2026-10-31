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
- **[código]** Árvore desde 2026-10-30: **40 tecnologias em 10 eras**. As 16 originais (Stone → Iron Age) mais 24 nossas, 4 por era: Classical (Philosophy, Aqueducts, Currency, Roads), Medieval (Crop Rotation, Castles, Universities, Windmills), Renaissance (Printing Press, Navigation, Gunpowder, Anatomy), Industrial (Steam Power, Railways, Vaccination, Industrial Farming), Modern (Electricity, Antibiotics, Flight, Rocketry), Information (Computers, Moon Landing, The Internet, Genetics). Custos de 26 mil a 384 mil pontos; cada era abre a partir da anterior; bônus nas mesmas faixas das originais. A era de uma tribo é a da tecnologia mais avançada que ela conhece; as invenções da LLM nascem na era atual da tribo, então quem passa a era passa a inventar coisas daquela época. **[executado]** md5 de regressão igual (em 3 mil dias ninguém sai da Idade do Ferro). Ritmo sem LLM (mundo do Arthur, seed 42): Bronze no ano 60, Ferro no 70, Clássica no 80, Medieval no 90. Com LLM vai bem mais rápido (invenções somam bônus de pesquisa).
- **[código]** Por que as pessoas ficam perto de casa: membros de uma tribo nunca passam do raio de território (`groups.territory_radius=14`, ou 8 a 24 pela coesão da política) e a cada dia têm chance de voltar um passo (`agents/behavior.py:_wander_or_return_home`). Só quem não tem tribo vaga pelo mapa todo. Uma tribo enorme (o reino do Arthur) fica toda espremida em volta da casa; a única forma de espalhar é dividir (colônia).
- **[código]** **Casas (opcional, 2026-10-30)** — `config.settlements.houses` (desligado no jogo, ligado no mundo do Arthur). Cada assentamento constrói 1 casa a cada `people_per_house=5` membros (até `max_houses=120`), dentro do domínio (6 + 2 × nível tiles, até `house_radius=14`), em tiles andáveis a pelo menos `house_spacing=2` de outra casa ou assentamento; as mais perto primeiro, com uma variação fixa (não usa o gerador aleatório). Cada membro mora numa delas, **para sempre** (`settlement.homes`; só quem perde a casa ou chega depois ganha uma, a menos cheia; uma casa só é abandonada quando sobra mais de uma) e é ela que o puxa de volta (`_social_context.home`), e ela também serve de despensa do celeiro (`_draw_ration`). `settlements.py:update_houses`. Mapa: `houseList` no `/state`; o mapa desenha as casas reais. **[executado]** md5 igual com a opção desligada; `tests/worldbox/test_houses.py`.
- **[executado]** Efeito medido (mundo do Arthur, sem LLM, seed 42, 30 anos; casas + raio 22 + coesão 0,45 contra o padrão): espalhamento médio da casa da tribo 3,0 → 4,1 tiles; população 308 → 248; tribos 10 → 8; batalhas 0 → 173 (42 mortos). Mais gente pelo território = mais encontros entre tribos vizinhas = escaramuças, que o padrão quase não tinha.
- **[código]** `culture.py`: difusão de conhecimento e troca de comida entre tribos amigas.

## Conflito e doença

- **[código]** `diplomacy.py:Diplomacy.update`: relações derivam para neutro, pioram com proximidade e escassez; guerra abaixo de `war_threshold`, paz por relação ou exaustão (`_should_end`).
- **[código]** `combat.py`: confrontos entre tribos hostis no mesmo espaço.
- **[código]** `epidemics.py`: doenças (`DISEASES`: fever, flux, pox, plague, coughing) espalham por vizinhança; sobreviventes ficam imunes.

## Eventos e história

- **[código]** `events.py:EventLog`: ring buffer (`SimulationConfig.event_log_size`) com `subscribe(listener)`; tipos em `EventKind` (inclui `MIND` para decisões de IA).
- **[código]** `chronicle.py:Chronicle`: só marcos (`Milestone`: era, primeira tecnologia, assentamento, população, guerra, praga, tribo, colapso), guardados para sempre. É a fonte do narrador.
