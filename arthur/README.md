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
| `GET /api/state` | ano, era, população, tribos, guerras; estado do LLM (disponível, ligado, chamadas, teto) |
| `GET /api/messages?since=` | mensagens da conversa depois do id `since` |
| `POST /api/send` `{text}` | manda uma mensagem ao rei; a resposta chega por `/api/messages` |
| `POST /api/llm` `{value: on\|off\|toggle, target: all\|arthur_chat}` | `all` (padrão): interruptor geral do jogo (tribos, narrador e Arthur); `arthur_chat`: só a conversa do Arthur |
| `GET /api/llm/report` | aba **LLMs**: fontes configuradas (modelo, endpoint, quem usa — nunca a chave), propósitos (mentes das tribos, narrador, conversa do Arthur, decisões do Arthur) com estado, controle e consumo, e o total |
| `POST /api/llm/cap` `{value}` | teto de chamadas por minuto das mentes (vazio = volta ao `.env`/config) |

## HUD

- **Conversa:** o chat com o rei.
- **LLMs:** mapa de quais LLMs existem, para que servem e quanto consomem; interruptor geral, interruptor próprio da conversa do Arthur e teto por minuto. Atualiza a cada 2 s com a aba aberta.
- O botão "LLM" no topo do painel é o interruptor geral, o mesmo do botão AI do mapa do jogo.

## Estado

**Etapa 1:** HUD e servidor próprios funcionando de ponta a ponta; as respostas vêm de um substituto offline (`advisor.placeholder_reply`), sem LLM. O rei de verdade (reino, persona, Gemini, decisões) chega nas etapas 2–4.

## Testes

```bash
.venv/bin/python -I -B tests/arthur/test_server.py "$PWD/arthur"
```

Sobe os dois servidores em portas de teste e cobre token, `Host`, `Origin` (inclusive a do mapa do jogo), tamanho do corpo, ida e volta da mensagem, interruptor de LLM compartilhado e o jogo intacto na própria porta.
