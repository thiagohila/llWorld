# Arthur — a parte do llWorld

O conselheiro do Rei Arthur, construído **ao lado** do jogo (`../worldbox`, o fork). O jogo mantém o mundo e as regras; o Arthur tem **HUD e servidor próprios** e cuida da conversa, da persona, das chamadas de LLM e das decisões do rei. Plano por etapas: `../docs/roadmap.md`.

## Divisão

| Jogo (fork) — `http://127.0.0.1:8765/` | Arthur — `http://127.0.0.1:8766/` |
|---|---|
| mundo, regras, simulação, mentes das tribos | conversa com o rei, persona, chamadas de LLM, decisões |
| HUD e mapa ao vivo (iguais aos de sempre) | HUD próprio, com o mapa do jogo num frame ao lado |
| interruptor e teto de LLM (`engine.minds`) | usa o mesmo interruptor e teto (botão "LLM" no HUD do Arthur) |
| aplica decisões no formato que já valida (`TribePolicy`) | decide a política do reino (`council.py`), no formato do jogo |

Os dois rodam no mesmo processo e compartilham o mesmo mundo (lendo sob `runner.lock`). O jogo nunca importa nada daqui; todo acesso ao jogo passa por `arthur/bridge.py`. O jogo também tem um mecanismo genérico de painéis (`LiveServer.add_extension`) que o Arthur **não** usa.

## Estrutura

```
arthur/
  run.py                entrypoint: jogo (8765) + Arthur (8766) no mesmo processo
  arthur/
    bridge.py           único ponto que importa o fork (põe ../worldbox no sys.path)
    persona.py          quem é o Arthur (nome, reino, idade, traços)
    kingdom.py          o reino no mundo: fundação, regras do rei, marca no mapa
    council.py          a mente do rei: decide a política do reino com a LLM
    quota.py            espera quando o provedor recusa por cota (429)
    advisor.py          a conversa com o rei (mensagens, interruptores, histórico)
    voice.py            a voz do rei: responde ao conselheiro com a LLM
    server.py           servidor do Arthur: página + /api protegida
    static/index.html   HUD do Arthur
```

## Rodar

Da raiz do llWorld, com a venv ativa:

```bash
python arthur/run.py                       # abre o HUD do Arthur
python arthur/run.py --no-ai --seed 42
python arthur/run.py --no-open --port 8765 --arthur-port 8766
```

`python -m worldbox.main --live` (dentro de `worldbox/`) continua rodando só o jogo, como antes.

## API do servidor (todas exigem o token da página no header `X-Arthur-Token`, `Host` local; POST exige `Origin` local; corpo ≤ 16 KB)

| Rota | Faz |
|---|---|
| `GET /` | HUD (com o token e a URL do mapa do jogo injetados) |
| `GET /api/state` | ano, era, população, tribos, guerras; estado do LLM (disponível, ligado, chamadas, teto); o rei (`king`: id, posição, saúde, reino, sede, povo, anos de reinado, se é o chefe) |
| `GET /api/messages?since=` | mensagens da conversa depois do id `since` |
| `POST /api/send` `{text}` | manda uma mensagem ao rei; a resposta chega por `/api/messages` |
| `POST /api/llm` `{value: on\|off\|toggle, target: all\|arthur_chat}` | `all` (padrão): interruptor geral do jogo (tribos, narrador e Arthur); `arthur_chat`: só a conversa do Arthur |
| `GET /api/llm/report` | aba **LLMs**: fontes configuradas (modelo, endpoint, quem usa — nunca a chave), propósitos (mentes das tribos, narrador, conversa do Arthur, decisões do Arthur) com estado, controle e consumo, e o total |
| `POST /api/llm/minds` `{value}` | quantas tribos (as maiores) a LLM governa (vazio = volta ao `.env`/config) |
| `POST /api/llm/cap` `{value}` | teto de chamadas por minuto das mentes (vazio = volta ao `.env`/config) |

## HUD

- **O rei:** nome, reino e sede, povo, anos de reinado e saúde; botão **Onde está o rei?** centraliza o mapa nele (por `postMessage`, já que o mapa é outra origem).
- **Conversa:** o chat com o rei.
- **Decisões:** a decisão atual do rei (postura, frase dele, justificativa, diplomacia, vetos) e as anteriores, com o motivo de cada uma (primeira decisão, intervalo, guerra mudou, celeiro baixo).
- **LLMs:** mapa de quais LLMs existem, para que servem e quanto consomem; interruptor geral, interruptor próprio da conversa do Arthur e teto por minuto. Atualiza a cada 2 s com a aba aberta.
- O botão "LLM" no topo do painel é o interruptor geral, o mesmo do botão AI do mapa do jogo.

## Estado

**Etapa 1:** HUD e servidor próprios funcionando de ponta a ponta. Sem LLM (`--no-ai` ou sem fonte), a conversa responde com um texto de teste marcado "(sem LLM)" (`advisor.placeholder_reply`).

**O mundo do Arthur** (`run.py:arthur_config`) difere do jogo padrão em:
- **População inicial:** **50** pessoas soltas (`INITIAL_POPULATION`; padrão 100) mais as 10 do reino — 60 no dia zero.
- **Casas:** ligadas (`HOUSES`) — cada pessoa mora numa casa espalhada pelo domínio da sua cidade (ver `docs/worldbox/02-simulacao.md`).
- **Andar mais longe de casa:** raio de território 22 (padrão 14) e chance diária de voltar 0,45 (padrão 0,55). Tribos com LLM e o rei ainda escolhem a própria coesão na política.
- Medido em 30 anos sem LLM: povo mais espalhado (3,0 → 4,1 tiles), um pouco menos gente (−19%) e escaramuças entre vizinhos (0 → 173 batalhas).
O jogo rodado sozinho continua com o padrão.

**Etapa 2 — o reino** (`kingdom.py`): no dia zero o "Kingdom of Arthur" é fundado no lugar mais fértil de uma amostra tirada da seed (mesma seed, mesmo lugar), com sede em Camelot e 10 pessoas. Tudo sem editar as regras do jogo, ajustando de fora e só para objetos marcados:

- **Arthur Pendragon, chefe fixo** — a escolha de chefe do jogo devolve sempre ele na tribo dele.
- **Imortal** — saúde nunca abaixo de 1 (nem dentro do combate, para ninguém ganhar um abate falso), imune a todas as doenças, idade fixa em 30 anos; o Smite do mapa desvia dele. Nenhuma morte é registrada para ele.
- **Um reino que só se divide quando o rei manda** — nunca se dissolve nem se divide sozinho. Passando do tamanho de divisão do jogo (55), o relatório avisa o rei e ele pode decidir `found_colony`: a divisão do próprio jogo roda uma vez (sai a parte mais longe de Camelot, cerca de 40%), o rei fica, e a colônia começa amiga (relação +40). A ordem vale por um dia: se o reino encolheu abaixo de 55 antes de a colônia partir, ela caduca (com aviso no log) em vez de dividir o reino sozinha depois. Se só o rei sobrar, chegam 6 colonos.
- **Fora das vagas de LLM das tribos** — as 3 vagas ficam com as outras tribos; o reino é decidido pela mente do próprio Arthur (etapa 3, abaixo).
- **No mapa** — anel dourado, plaquinha "Arthur" com coroa e ponto no minimapa (recurso genérico do jogo, `LiveState.feature`).
- **Reset do mundo** refunda o reino.

**Etapa 3 — a mente do rei** (`council.py`): o reino é decidido pelo Arthur, não pelas mentes do jogo.

- **O que ele lê:** a persona (temperamento, objetivos, linhas vermelhas, voz) no prompt de sistema e o mesmo relatório que qualquer tribo recebe (`_brief_tribe` do jogo: povo, fome, celeiro, profissões, tecnologias, vizinhos e relações, materiais), mais a última decisão dele. v1: sem conhecimento limitado.
- **O que ele devolve:** `{"policy": {...formato do jogo...}, "found_colony": true|false, "rationale": "..."}` — o prompt mostra só o formato, sem valores de exemplo (com um exemplo concreto ele copiava: decidiu "farm" 15 de 16 vezes, 6 delas com a frase do exemplo) — a frase (`intent`) em inglês, porque vai para o log do jogo; a justificativa em português, para o HUD. Também aceita a política "solta" (formato do `mock`).
- **Validação:** a do jogo (`parse_policy`), mais a do Arthur: descarta tribo desconhecida ou ele mesmo, descarta invenção que o terreno não sustenta, e a **linha vermelha** — nada de guerra contra quem não está em guerra conosco e tem relação ≥ 0; um `raid` sem inimigo vira `defend`. Resposta vazia ou inválida mantém a política anterior e espera mais (backoff). Cada veto diz quem vetou: **o rei** (linha vermelha) ou **o jogo** (tribo inexistente, invenção impossível ou acima do limite de invenções próprias — 100 por tribo). Quando o reino chega ao limite, o relatório avisa o rei para não propor mais (economiza tokens).
- **Quando pensa:** no primeiro dia; depois a cada 40 dias de jogo (o mesmo intervalo das tribos, no mínimo 20 s reais entre chamadas, pulando se nada mudou); antes disso se uma guerra começa ou termina ou se o celeiro cai abaixo de 25% (de novo só depois de voltar acima de 40%), com no mínimo 10 dias entre pensamentos antecipados.
- **Custo:** mesmo interruptor geral e mesmo teto por minuto das tribos; interruptor próprio ("Decisões do Arthur") na aba LLMs; consumo separado lá. Fonte: a do `.env` (Gemini). `--no-ai` desliga ele também.
- **Cota esgotada (429):** o rei para de tentar e espera — 1 min, depois 5, 15, 30 e 1 h a cada 429 seguido; qualquer resposta boa zera (`quota.py`, compartilhado com a conversa). O HUD mostra "esperando a cota da LLM (429)" e quando tenta de novo. Motivo: o plano grátis do Gemini esgotou numa noite e o rei insistiu ~230 vezes em vão. As tribos do jogo seguem o próprio ritmo (continuam tentando).
- **Como chega ao mundo:** o motor lê a política dele por `engine.minds.policy_for`; a diplomacia é empurrada pelo próprio conselho, todo dia, nos mesmos valores das tribos. Ele não ocupa vaga de LLM das tribos (no HUD do jogo, o contador geral de "mentes" passa a incluir o reino, porque lê por `policy_for`).

**Etapa 4a — a voz do rei** (`voice.py`): o rei responde ao conselheiro.

- **O que ele lê:** a persona, o mesmo relatório do conselho (sem as instruções de invenção), as 3 últimas decisões dele com a justificativa, o dia e o ano, e as últimas 6 trocas da conversa. Só sabe o que o relatório diz; se não sabe, diz que não sabe.
- **O que ele devolve:** `{"reply": "...", "advice": null | {"summary", "verdict": accept|consider|reject|clarify, "urgent"}}`. A resposta em português, em personagem; a leitura do conselho aparece embaixo da fala no HUD ("conselho: … · vai considerar"). Urgente só vale se ele aceita ou considera. Se o modelo ignora o formato mas escreve texto, o texto vale.
- **Nunca muda o mundo:** conversar não decide nada; ele diz no máximo que vai pesar no próximo conselho. (Etapa 4b: o conselho entra na próxima decisão.)
- **Custo:** mesmo interruptor geral, mesmo teto por minuto (cada mensagem conta), mesma espera por cota (429) do conselho, mais o interruptor próprio da conversa na aba LLMs. Bloqueado → aviso no chat, sem chamada. Falha da LLM → "Preciso pensar nisso…" em personagem e uma nota com o motivo.
- **Idioma:** as instruções ao modelo estão em inglês (como no conselho); a fala do rei é em português.

## Testes

```bash
for t in tests/arthur/test_*.py; do .venv/bin/python -I -B "$t" "$PWD/arthur" | tail -1; done
```

`test_voice.py` cobre a conversa (API simulada): resposta, prompt (persona, relatório, decisões), histórico limitado, leitura do conselho, formato ignorado, falhas, teto, cota, interruptores, erro fatal, `--no-ai`. `test_council.py` cobre a mente (API simulada, sem rede): primeira decisão, cadência, teto compartilhado, interruptores, gatilho de guerra, espera por cota (429), linha vermelha, respostas inválidas, formato do `mock`, "esquecer", erro fatal, resposta velha descartada após reset, `--no-ai`. `test_kingdom.py` cobre o reino: fundação no dia zero, mesma seed → mesmo lugar, anos de jogo, fome, ferimento, doença, Smite, colonos, divisão, vagas de LLM e reset. `test_server.py` sobe os dois servidores em portas de teste e cobre token, `Host`, `Origin` (inclusive a do mapa do jogo), tamanho do corpo, ida e volta da mensagem, interruptor de LLM compartilhado e o jogo intacto na própria porta.
