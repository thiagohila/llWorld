# Rascunho — design da IA do worldbox-ai

> **Status: rascunho, não aprovado.** Escrito em 2026-10-20 como ideia antecipada; revisar com o Thiago antes da etapa 3 do `../roadmap.md`. Não usar como especificação sem essa revisão.
>
> **Mudou desde então (2026-10-21):** o backoff após falha já existe no fork; `chat()` aceita qualquer fonte compatível com OpenAI e a mente `mock` (desenvolvimento sem custo); `MindDirector` expõe uso e teto por minuto; o contrato atualizado de interfaces está no `../roadmap.md` (ele prevalece sobre a seção 3 abaixo).

Design da camada de IA do llWorld para o protótipo "conselheiro do Rei Arthur". Define **o que a LLM vê, de onde isso vem, o que ela pode devolver e como o jogo valida e aplica**. Não é código; é o contrato que o código do `worldbox-ai/` vai seguir.

Base: `llWorld-visao-produto.md` (o quê) e `docs/worldbox/` (como o fork funciona). Legenda: **[código]** confirmado no fork · **[hipótese]** a validar · **[decisão]** escolha de design desta proposta · **[aberto]** decisão pendente do produto.

---

## 1. Princípios

1. **A simulação é a verdade.** A LLM nunca lê nem escreve o estado bruto do motor. Ela recebe uma *projeção* do mundo filtrada pelo que Arthur sabe, e devolve *propostas* que o jogo valida.
2. **O vocabulário de ação é o que o motor executa.** Arthur só pode decidir coisas que o fork sabe fazer acontecer (seção 6). Nada de ações "narradas" sem efeito.
3. **Conversar não muda o mundo.** O chat altera apenas a memória e a agenda de Arthur. O mundo só muda pela decisão do conselho, que passa pela validação. (Invariante — seção 5.)
4. **Influenciar ≠ controlar.** O conselho do jogador entra como *um insumo entre vários* no contexto da decisão, com peso dado pela confiança e pelos objetivos de Arthur. Não existe caminho do jogador até a política sem passar pela LLM e pelo validador.
5. **Números vêm da simulação, não da LLM.** Confiança, histórico de conselhos e consequências são medidos em deltas do mundo. A LLM pode no máximo sugerir sinais limitados.
6. **Determinístico onde dá.** Percepção, memória, recuperação e orçamento de contexto são código puro e testável. A LLM é o único componente não determinístico, e fica atrás de um gateway substituível.

## 2. Visão geral

```
                 ┌──────────────── worldbox (fork, intocado) ────────────────┐
                 │ SimulationEngine.step()  EventLog  Diplomacy  Groups ...  │
                 │        ▲ engine.minds = CouncilDirector (subclasse)       │
                 └────────┼─────────────────────┬────────────────────────────┘
                          │ TribePolicy validada│ eventos (subscribe) + snapshot sob lock
┌─────────────────────────┼─────────────────────┼──── worldbox-ai ───────────────────────┐
│  bridge/  (único módulo que importa worldbox)  ▼                                        │
│     engine_adapter ──► KingdomView (dataclasses puras)   event_ingest ──► memória       │
│                                                                                         │
│  perception/  filtro de conhecimento: o que Arthur sabe, com idade da informação        │
│  memory/      episódios · crenças · agenda · registro do conselheiro (confiança)        │
│  context/     montagem em camadas, orçamento por seção, render                         │
│  loops/       council (decide política)      conversation (responde ao jogador)        │
│  llm/         gateway (client.chat do fork | fake | replay) · schemas · validação       │
│  telemetry/   trace JSONL por chamada                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                          ▲ chat (HTTP próprio, outra porta)
                       jogador
```

Dois loops de LLM, separados de propósito:

| Loop | Quando | Lê | Pode produzir | Muda o mundo? |
|---|---|---|---|---|
| **Conversa** | a cada mensagem do jogador | persona, visão do reino, memória, agenda, conversa | resposta em personagem, avaliação do conselho, notas de memória, itens de agenda | **Não** |
| **Conselho** | cadência fixa + gatilhos | persona, visão do reino, memória, agenda (com conselhos pendentes), confiança | `TribePolicy` + justificativa + quais conselhos pesaram | **Sim**, via `parse_policy` |

## 3. Integração com o fork (sem editá-lo)

| Necessidade | Ponto de extensão | Status |
|---|---|---|
| Substituir a mente da tribo do Arthur | `engine.minds` é atributo público; o motor só chama `tick`, `reset`, `policy_for`, `thinking_count`; `LiveState` e o terminal chamam `snapshot` e `policy_for`. Uma subclasse `CouncilDirector(MindDirector)` atribuída após construir o motor cobre todos os usos. As demais tribos continuam com o comportamento original via `super()`. | **[código]** |
| Arthur fixo como líder | `engine._process_roles_and_leadership` chama `culture_system.choose_chieftain` pelo módulo. Envolver `worldbox.society.culture.choose_chieftain` de fora ("se Arthur está vivo entre os membros, é ele") funciona sem editar o fork. Trade-off: é um patch global no processo, frágil a mudanças upstream. Alternativa: um gancho mínimo no fork. | **[código]** seam existe · **[aberto]** qual usar |
| Backoff após falha de API | já corrigido no fork (`d6472e1`): espera crescente e parada em erro fatal. | **[código]** |
| Observar o mundo | `engine.events.subscribe(listener)`. | **[código]** |
| Chat | Servidor HTTP próprio do `worldbox-ai`, outra porta, mesmo processo, compartilhando `engine` e `runner.lock`. O handler do fork fica intocado. Exige um entrypoint próprio que monte engine + runner + `LiveServer` do fork + servidor de chat. | **[decisão]** |
| Chamar a LLM | Reusar `worldbox.ai.client.chat` (erros como valor, retentativa, TLS, fontes do `.env`, `mock`, `status`/tokens). Não duplicar. Dividir o teto por minuto com as mentes das tribos. | **[decisão]** |
| Importar o fork | O fork não é instalável (sem `pyproject`). Opção v1: o entrypoint do `worldbox-ai` insere `worldbox/` no `sys.path` em um único lugar (`bridge/`). | **[decisão]** |

## 4. As camadas de contexto

Ordem fixa, do mais estável ao mais volátil. Estável primeiro favorece cache de prefixo quando o provedor oferece; o comportamento de cache de cada provedor **[hipótese]** deve ser verificado, não assumido.

| # | Camada | Fonte | Muda quando | Orçamento inicial* |
|---|---|---|---|---|
| L0 | **Contrato do sistema**: papel, regras de honestidade, schema de saída | `prompts/*.md` versionados | nova versão do prompt | 500 |
| L1 | **Persona**: quem é Arthur, traços, valores, objetivos com prioridade, limites, estilo de fala | `persona/arthur.json` | raramente; mudanças de caráter vêm de eventos (seção 8) | 400 |
| L2 | **Visão do reino**: estado percebido do mundo | `perception/` sobre o snapshot | todo turno/decisão | 900 |
| L3 | **Memória recuperada**: episódios e crenças relevantes | `memory/` + recuperação | todo turno/decisão | 600 |
| L4 | **Agenda e conselheiro**: intenções abertas, conselhos pendentes, confiança e histórico do conselheiro | `memory/agenda`, `memory/trust` | todo turno/decisão | 300 |
| L5 | **Conversa**: resumo acumulado + últimos turnos | `loops/conversation` | todo turno (só no loop de conversa) | 1200 |
| L6 | **Tarefa**: "responda ao conselheiro" ou "decida a política agora" + schema | código | fixo por loop | 150 |

\* Tokens aproximados; **valores iniciais a calibrar**, configuráveis por seção. Não fixar janela de contexto de modelo no código.

Regras de orçamento: cada camada tem teto próprio; ao estourar, corta dentro da camada (itens de menor relevância primeiro), nunca rouba de L0/L1/L6. L2 corta vizinhos distantes antes de dados do próprio reino. L5 resume turnos antigos antes de descartar.

### L1 — Persona (formato)

```json
{
  "id": "arthur", "name": "Arthur", "title": "Rei",
  "traits": {"aggression": 0.35, "caution": 0.55, "industry": 0.6},
  "temperament": ["justo", "orgulhoso", "leal aos seus"],
  "goals": [
    {"id": "security",   "text": "Manter o reino a salvo",       "priority": 1},
    {"id": "prosperity", "text": "Celeiros cheios e povo crescendo", "priority": 2},
    {"id": "renown",     "text": "Ser lembrado como rei justo",  "priority": 3}
  ],
  "red_lines": ["não atacar quem está em paz conosco sem provocação"],
  "voice": "fala com dignidade, frases curtas, chama o jogador de 'conselheiro'"
}
```

`traits` são os mesmos do agente no fork e são aplicados ao agente de Arthur (via chefe, puxam a agressividade da tribo — `apply_chieftain_influence` **[código]**). O resto é só narrativo/decisório.

### L2 — Visão do reino (percepção)

Construída por `perception/` a partir de um `KingdomView` extraído sob lock. Seções:

- **Tempo:** ano, dia, estação **[hipótese: o fork não tem estação]**.
- **O reino** (conhecimento total): população, fome média, profissões, celeiro, assentamento e nível, tecnologias, guerras, baixas, política vigente e desde quando.
- **Vizinhos** (conhecimento parcial): só tribos dentro de um raio de contato ou com histórico de interação; cada item com `last_seen_day`. Dados de tribo fora de contato não aparecem.
- **Ameaças e oportunidades:** derivadas por regra (relação abaixo de X e distância abaixo de Y; vizinho com fome alta; celeiro abaixo de Z).
- **Alegações não verificadas:** informações trazidas pelo jogador, marcadas como `claim` com fonte, nunca misturadas com observação.

Todo vizinho é referenciado por `tribe_id` estável. **[código]** O fork expõe tudo (`relation_summary`, `_brief_tribe` veem todas as tribos); o filtro de conhecimento é responsabilidade do `worldbox-ai`.

### L3 — Memória

Três estruturas, todas código determinístico:

- **Episódios:** `{day, kind, text, entities:[tribe_id...], salience, source: observed|told|advisor}`. Alimentados por `EventLog.subscribe` com filtro (envolve o reino, um vizinho conhecido ou o próprio Arthur) e por conversas. `salience` por regra (guerra > morte de chefe > invenção > fundação...).
- **Crenças:** frases curtas sobre entidades, com confiança e evidências (`"Tribo 4 é traiçoeira" ← [ep 12, ep 31]`). v1: criadas pela LLM como `memory_notes` validadas; consolidação periódica é **[aberto]**.
- **Registro do conselheiro:** ver L4.

Recuperação v1 (sem embeddings): `score = salience × decaimento(idade) + bônus se compartilha entity_id com o assunto atual`. Top-k dentro do orçamento.

### L4 — Agenda e conselheiro

- **Agenda:** intenções abertas de Arthur (`"considerar aliança com tribo 3"`), com origem (conselho, evento, persona) e prazo.
- **Conselhos pendentes:** cada conselho do jogador vira um item `{advice_id, day, text, topic_entities, arthur_verdict}` até o próximo conselho.
- **Confiança:** número 0..1 e histórico, calculados pela simulação (seção 7).

## 5. Contratos de saída e validação

### Loop de conversa

```json
{
  "reply": "texto em personagem",
  "advice": {"present": true, "summary": "...", "verdict": "accept|consider|reject|clarify", "reason": "..."},
  "memory_notes": [{"text": "...", "entities": [3]}],
  "agenda": [{"text": "...", "entities": [3], "due_in_days": 30}],
  "trust_signal": 0.0
}
```

Validação: `entities` precisam existir e ser conhecidas por Arthur; textos truncados; `trust_signal` limitado a ±0,05 e só entra como ajuste leve (seção 7); itens inválidos descartados, não corrigidos. Falha total → resposta de fallback em personagem ("Preciso pensar nisso") sem efeitos.

**Invariante:** nada deste schema toca o motor.

### Loop de conselho

```json
{
  "policy": { "...": "mesmo formato JSON que o fork já aceita em parse_policy" },
  "rationale": "por que, em uma ou duas frases",
  "advice_considered": [{"advice_id": "a7", "followed": true, "weight": 0.6}]
}
```

Validação em duas etapas:
1. **Do fork:** `worldbox.ai.minds.parse_policy` (limites, aliases, invenções por material) **[código]**.
2. **Do worldbox-ai:** `toward` só com tribos conhecidas por Arthur; respeito a `red_lines` checáveis por regra; `{}` ou política vazia **rejeitada** (o fork aceita e substitui pela padrão — **[código]**); `advice_id` inexistente descartado.

Falha → mantém a política anterior e registra erro com backoff.

## 6. Vocabulário de ação (o que Arthur pode decidir)

Mapeamento dos exemplos da visão para o que o fork executa:

| Intenção na visão | Campo(s) da `TribePolicy` | Efeito no fork |
|---|---|---|
| Preparar defesas | `stance: defend`, `warrior_share` ↑, `cohesion` ↑ | profissões, territorialidade **[código]** |
| Negociar / acordo comercial | `toward: [{tribe_id, action: peace|trade}]` | relação sobe a cada dia **[código]** |
| Declarar guerra / pressionar | `toward: war`, `stance: raid`, `fight` ↑ | relação cai a cada dia até a guerra **[código]** |
| Priorizar comida / estocar | `stance: farm`, `farmer_share` ↑, `seek_food` ↑ | colheita, celeiro **[código]** |
| Expandir | `stance: expand`, `cohesion` ↓ | raio de território maior **[código]** |
| Investir em conhecimento | `stance: research`, `scholar_share` ↑, `invent` | pesquisa +20%, invenções **[código]** |
| Investigar intenções / enviar emissários / espiões | — | **sem suporte no fork.** Fora da v1 ou exige trabalho na simulação. O loop de conversa nunca pode afirmar que Arthur fez isso. |

**Magnitude é design de jogo.** `toward` é aplicado todo dia: um `war` ≈ −128 de relação em 40 dias **[código]**. A cadência do conselho e esses deltas definem quão rápido um conselho vira guerra — parâmetro de gameplay, não só de custo.

## 7. Influência e confiança

- O conselho só chega ao mundo assim: chat → item de agenda → contexto da próxima decisão → LLM decide → validação → política.
- **Peso do conselho** no contexto: apresentado junto da confiança atual e do histórico; a persona instrui Arthur a pesar conselhos contra seus objetivos. Não há regra que force aceitação.
- **Confiança calculada pela simulação:** quando uma decisão marca `followed: true`, abre-se uma janela de avaliação de N dias. Ao fechar, mede-se o delta das métricas ligadas ao tema (relação com o alvo, comida no celeiro, mortos em guerra, população). Bom resultado ↑ confiança, mau ↓. `trust_signal` da conversa é só um ajuste pequeno (simpatia/desconfiança no diálogo).
- O histórico ("seu conselho sobre a tribo 4 terminou em guerra") vira episódio de memória com alta saliência — atende "uma recomendação desastrosa pode ser lembrada".

## 8. Tempo e cadência

- O mundo nunca espera a LLM (padrão do fork: snapshot sob lock → chamada fora → resultado aplicado no próximo `tick`) **[código]**.
- **Conselho:** a cada N dias (inicial: igual ao `think_interval_days=40` do fork) **e** em gatilhos: guerra declarada/terminada envolvendo o reino, celeiro abaixo de um limiar, vizinho novo em contato, conselho marcado como urgente.
- **Conversa:** assíncrona. Enquanto Arthur "pensa", o mundo anda; a resposta reflete o snapshot do momento da pergunta, e isso é dito no contexto ("dia X").
- **Mudança de caráter** (visão §6): v1 só via crenças e confiança; ajuste de `traits` por eventos é **[aberto]**.

## 9. Observabilidade e testes

- **Trace JSONL** por chamada: loop, dia, versão do prompt, tamanho de cada camada, modelo, latência, resposta crua, erros de validação, efeitos aplicados. Permite replay e depuração de "por que Arthur fez isso".
- **Gateway com provedores trocáveis:** `fork` (`client.chat`), `fake` (respostas roteirizadas), `replay` (lê um trace). O fork já tem a mente `mock` (`LLM_BASE_URL=mock`) para as tribos — o Arthur pode ganhar um `mock` equivalente.
- **Testes unitários** (stdlib `unittest`, sem rede): percepção, recuperação, orçamento, validação — tudo sobre dataclasses, sem motor.
- **Testes de cenário** (seed + conselhos roteirizados + provedor fake/replay), alinhados aos critérios da visão §11:
  - Arthur pode recusar (verdict `reject` não gera mudança de política ligada ao conselho);
  - o mesmo conselho em situações diferentes produz contextos diferentes;
  - uma decisão aplicada muda o mundo de forma mensurável (diff de política → diff de relação/profissões em N dias);
  - nenhuma referência a tribo desconhecida passa pela validação.
- **Regressão do fork:** `--no-ai --seed 42 --days 3000` sem chaves continua com o mesmo md5.

## 10. Estrutura proposta do `worldbox-ai/`

```
worldbox-ai/
  run.py                    entrypoint: engine + runner + LiveServer do fork + chat
  llworld_ai/
    bridge/                 ÚNICO lugar que importa worldbox
      engine_adapter.py     snapshot → KingdomView; aplica política
      director.py           CouncilDirector(MindDirector)
      event_ingest.py       EventLog.subscribe → episódios
      chat_server.py        HTTP do chat (outra porta)
    persona/                persona.py + arthur.json
    perception/             view.py (dataclasses), knowledge.py (filtro), threats.py
    memory/                 episodes.py, beliefs.py, agenda.py, trust.py, retrieval.py
    context/                layers.py, budget.py, render.py
    loops/                  council.py, conversation.py
    llm/                    gateway.py, providers.py, schemas.py, validate.py
    telemetry/              trace.py
  prompts/                  council.md, conversation.md (versionados)
  tests/                    unit/, scenarios/
```

Regra de dependência: `bridge → (tudo)`; nenhum outro pacote importa `worldbox`. Assim, todo o resto é testável sem o motor.

## 11. Decisões em aberto

1. **Quem é o reino de Arthur no mundo?** Tribo fundada no dia 0 (estilo `found_civ`) ou tribo existente "adotada"?
2. **Morte de Arthur:** idade, peste ou batalha podem matá-lo. Imortal no protótipo (ex.: `lifespan_days` alto) ou sucessão como mecânica?
3. **Divisão e dissolução:** a tribo se divide ao passar de 55 e se dissolve abaixo de 4 **[código]**. Qual grupo continua sendo "o reino"? Bloquear divisão do reino?
4. **Líder fixo:** patch de `choose_chieftain` por fora vs. gancho mínimo no fork.
5. **`--no-ai`:** `MindDirector.tick` sai cedo com `config.enabled=False` **[código]**; uma subclasse compartilhando `AIConfig` desliga Arthur junto. Desejado?
6. **Conhecimento:** raio de contato, atraso de notícias, alegações falsas de outros personagens.
7. **Idioma:** Arthur fala português com o jogador; prompts internos em inglês ou português?
8. **Modelo:** o mesmo do fork (`deepseek-flash`) para os dois loops, ou modelo mais capaz para a conversa?
