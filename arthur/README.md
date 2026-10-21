# Arthur — a parte do llWorld

O conselheiro do Rei Arthur, construído **ao lado** do jogo (`../worldbox`, o fork). O jogo mantém o mundo e as regras; o Arthur tem **HUD e servidor próprios** e cuida da conversa, da persona, das chamadas de LLM e das decisões do rei. Plano por etapas: `../docs/roadmap.md`.

## Divisão

| Jogo (fork) — `http://127.0.0.1:8765/` | Arthur — `http://127.0.0.1:8766/` |
|---|---|
| mundo, regras, simulação, mentes das tribos | conversa com o rei, persona, chamadas de LLM, decisões |
| HUD e mapa ao vivo (iguais aos de sempre) | HUD próprio, com o mapa do jogo num frame ao lado |
| interruptor e teto de LLM (`engine.minds`) | usa o mesmo interruptor e teto (botão "LLM" no HUD do Arthur) |
| aplica decisões no formato que já valida (`TribePolicy`) | propõe as decisões do rei (etapas 3+) |

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
    advisor.py          a conversa com o rei
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

**Etapa 1:** HUD e servidor próprios funcionando de ponta a ponta; as respostas vêm de um substituto offline (`advisor.placeholder_reply`), sem LLM.

**População inicial:** o mundo do Arthur começa com **50** pessoas soltas (`INITIAL_POPULATION` em `run.py`; o padrão do jogo é 100) mais as 10 do reino — 60 no dia zero. O jogo rodado sozinho continua com 100.

**Etapa 2 — o reino** (`kingdom.py`): no dia zero o "Kingdom of Arthur" é fundado no lugar mais fértil de uma amostra tirada da seed (mesma seed, mesmo lugar), com sede em Camelot e 10 pessoas. Tudo sem editar as regras do jogo, ajustando de fora e só para objetos marcados:

- **Arthur Pendragon, chefe fixo** — a escolha de chefe do jogo devolve sempre ele na tribo dele.
- **Imortal** — saúde nunca abaixo de 1 (nem dentro do combate, para ninguém ganhar um abate falso), imune a todas as doenças, idade fixa em 30 anos; o Smite do mapa desvia dele. Nenhuma morte é registrada para ele.
- **Um reino só** — não se divide nem se dissolve; se só o rei sobrar, chegam 6 colonos.
- **Fora das LLMs por enquanto** — segue as regras normais e não ocupa uma das vagas de LLM (as outras tribos ficam com elas). A mente própria do Arthur é a etapa 3.
- **No mapa** — anel dourado, plaquinha "Arthur" com coroa e ponto no minimapa (recurso genérico do jogo, `LiveState.feature`).
- **Reset do mundo** refunda o reino.

**Etapa 3 — a mente do rei** (`council.py`): o reino é decidido pelo Arthur, não pelas mentes do jogo.

- **O que ele lê:** a persona (temperamento, objetivos, linhas vermelhas, voz) no prompt de sistema e o mesmo relatório que qualquer tribo recebe (`_brief_tribe` do jogo: povo, fome, celeiro, profissões, tecnologias, vizinhos e relações, materiais), mais a última decisão dele. v1: sem conhecimento limitado.
- **O que ele devolve:** `{"policy": {...formato do jogo...}, "rationale": "..."}` — a frase (`intent`) em inglês, porque vai para o log do jogo; a justificativa em português, para o HUD. Também aceita a política "solta" (formato do `mock`).
- **Validação:** a do jogo (`parse_policy`), mais a do Arthur: descarta tribo desconhecida ou ele mesmo, descarta invenção que o terreno não sustenta, e a **linha vermelha** — nada de guerra contra quem não está em guerra conosco e tem relação ≥ 0; um `raid` sem inimigo vira `defend`. Resposta vazia ou inválida mantém a política anterior e espera mais (backoff).
- **Quando pensa:** no primeiro dia; depois a cada 40 dias de jogo (o mesmo intervalo das tribos, no mínimo 20 s reais entre chamadas, pulando se nada mudou); antes disso se uma guerra começa ou termina ou se o celeiro cai abaixo de 25% (de novo só depois de voltar acima de 40%), com no mínimo 10 dias entre pensamentos antecipados.
- **Custo:** mesmo interruptor geral e mesmo teto por minuto das tribos; interruptor próprio ("Decisões do Arthur") na aba LLMs; consumo separado lá. Fonte: a do `.env` (Gemini). `--no-ai` desliga ele também.
- **Como chega ao mundo:** o motor lê a política dele por `engine.minds.policy_for`; a diplomacia é empurrada pelo próprio conselho, todo dia, nos mesmos valores das tribos. Ele não ocupa vaga de LLM das tribos (no HUD do jogo, o contador geral de "mentes" passa a incluir o reino, porque lê por `policy_for`).

O rei ainda não conversa de verdade: isso é a etapa 4.

## Testes

```bash
for t in tests/arthur/test_*.py; do .venv/bin/python -I -B "$t" "$PWD/arthur" | tail -1; done
```

`test_council.py` cobre a mente (API simulada, sem rede): primeira decisão, cadência, teto compartilhado, interruptores, gatilho de guerra, linha vermelha, respostas inválidas, formato do `mock`, "esquecer", erro fatal, resposta velha descartada após reset, `--no-ai`. `test_kingdom.py` cobre o reino: fundação no dia zero, mesma seed → mesmo lugar, anos de jogo, fome, ferimento, doença, Smite, colonos, divisão, vagas de LLM e reset. `test_server.py` sobe os dois servidores em portas de teste e cobre token, `Host`, `Origin` (inclusive a do mapa do jogo), tamanho do corpo, ida e volta da mensagem, interruptor de LLM compartilhado e o jogo intacto na própria porta.
