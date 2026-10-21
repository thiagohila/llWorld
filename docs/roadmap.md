# Roadmap — estado atual e próximas etapas

Atualizado em 2026-10-21. O *quê* está em `../llWorld-visao-produto.md`; ideias de design (não aprovadas) em `rascunhos/arthur-design.md`; decisões pendentes em `pendencias/projeto.md`.

## Estado atual

### O jogo — fork `worldbox/` em `bbbea3a` (funcionando)

Roda como veio do `ryfcx/worldbox`, com melhorias pontuais — nenhuma regra de simulação mudou (md5 de regressão idêntico desde o início):

| Área | Situação | Commit |
|---|---|---|
| Interface | HUD de jogo, abas, log com filtros, minimapa, atalhos; poderes com efeito, aviso e log | `b10f9fb` |
| Arte | spritesheets do Claude Design (pessoas, overlays, prédios, terreno, props) com troca de cor por tribo; fallback gerado | `6804118` |
| Performance | −27–33% de custo por dia; velocidades viraram taxas reais | `bfe84cd` |
| IA das tribos | fontes grátis por `.env` (Gemini testado), mente offline `mock`, controle de custo, backoff, contadores no HUD | `d6472e1` |
| Correções | Smite matava 0 de 14 (agora mata), narrador só com DeepSeek, política `{}` | `d6472e1` |

Ainda em aberto no jogo: segurança do servidor local (CSRF, DNS rebinding), determinismo com duas chaves, sem suíte de testes — ver `pendencias/jogo.md`.

### O projeto — repo `llWorld`

- Docs de referência do fork (`docs/worldbox/01..08`), ambiente e versões (`ambiente.md`), checklists, agentes `worldbox-guide` e `sim-runner`.
- `.venv` com Python 3.14; remotes: `thiagohila/llWorld` e `thiagohila/worldbox` (push para o upstream bloqueado).
- `arthur/` (Arthur) existe desde a etapa 1: HUD e servidor próprios (porta 8766, com o mapa do jogo num frame), ponte de import, conversa com respostas de teste sem LLM — ver `../arthur/README.md`.
- Etapa 2: o **reino do Arthur** é fundado no dia zero (`arthur/arthur/kingdom.py`): Arthur Pendragon chefe fixo e imortal, reino que não se divide nem se dissolve, fora das vagas de LLM, com plaquinha dourada no mapa e botão "Onde está o rei?" no HUD do Arthur.

## Camadas e interfaces

```
llWorld/
  worldbox/      fork — regras do mundo, simulação, mapa ao vivo, mentes das tribos
  arthur/        nosso — Arthur, conselheiro, chat, memória, decisões de alto nível
```

**Regra:** Arthur usa o jogo só pelas interfaces abaixo; `worldbox` nunca importa Arthur. Mudança no fork só quando não houver interface — e então mínima, genérica e commitada no submódulo (decisão a fechar em `pendencias/projeto.md`).

### Contrato: o que o Arthur usa do jogo

| Para quê | Interface no fork | Status |
|---|---|---|
| Criar e rodar o mundo | `SimulationEngine(config, seed)`, `step()`; `SimulationRunner` (`lock`, `start`, `pause`, `set_delay`) | **pronto** [código] |
| Mapa ao vivo junto | `cli.webview.LiveServer(engine, runner)` no mesmo processo | **pronto** [código] |
| Ler o estado | `engine.groups` / `settlements` / `diplomacy` / `agents` / `chronicle`, sempre sob `runner.lock`; ou `GET /state` | **pronto** [código] |
| Observar acontecimentos | `engine.events.subscribe(fn)` — recebe todos os tipos, inclusive os poderes (`SYSTEM`) que o feed HTTP omite | **pronto** [código] |
| Decidir pela tribo do Arthur | subclasse de `ai.minds.MindDirector` atribuída a `engine.minds`; validar com `parse_policy` / `TribePolicy` | **pronto** [código] |
| Chamar a LLM | `ai.client.chat()` com as fontes do `.env` (DeepSeek, OpenAI, compatível com OpenAI, `mock`); `ChatResult` traz `status`, `fatal`, tokens | **pronto** [código] |
| Ligar/desligar LLM em jogo | `engine.minds.paused` / `set_paused()`, `set_call_cap()`, `forget_policies()`; HTTP `/control?action=ai` / `ai_cap` / `ai_forget`; botão **AI** e tecla `M` no HUD; `ai on/off/cap/forget` no terminal | **pronto** [código] |
| Controlar custo | `MindDirector` já limita as tribos; o loop do Arthur **usa o mesmo teto** (`call_cap`, `calls_last_minute`) e **respeita `paused`** | **a fazer** no Arthur |
| Fundar o reino | `society.founding.found_tribe` / `settle_people` (extraídos de `LiveState.found_civ`, que agora os usa; comportamento idêntico) | **pronto** [executado] |
| Arthur fixo como chefe | patch por fora em `society.culture.choose_chieftain` (chamado via módulo), só para o agente marcado `llworld_king` | **pronto** [executado] |
| Arthur imortal (sem sucessão) | por fora: `KingNeeds` (saúde nunca abaixo de 1, nem na hora do combate), imunidade permanente a todas as doenças, idade fixa; Smite do mapa desvia dele (envolve `LiveState.act`) — nenhuma morte ou abate é contado para ele | **pronto** [executado] |
| Reino não se divide nem se dissolve | patch por fora em `GroupRegistry.try_split` / `find_unviable`, só para a tribo marcada `llworld_realm`; se só o rei sobrar, chegam 6 colonos | **pronto** [executado] |
| Reino fora das mentes de LLM | `engine.minds._eligible` reimplementado na instância sem o reino (as 3 vagas vão para as outras tribos) | **pronto** [executado] |
| Reset do mundo | `engine.reset` envolvido na instância: refunda o reino; as marcas ficam nos objetos, não nos ids | **pronto** [executado] |
| Marcar o rei no mapa | `LiveState.feature(agent_id, label, kind)` / `unfeature` → `featured` no `/state`; o mapa desenha anel dourado + plaquinha (coroa para `kind="king"`) e ponto no minimapa | **pronto** [executado] |
| Centralizar o mapa nele | `postMessage({type:"worldbox:focus", id})` do HUD do Arthur para o frame; o mapa só ouve a janela-mãe e só move a vista | **pronto** [executado] |
| Chat (HTTP) | servidor próprio do Arthur (`arthur/arthur/server.py`, porta 8766, mesmo processo): `/api/state`, `/api/messages`, `/api/send`, `/api/llm`; token + `Host` + `Origin` + limite de corpo | **pronto** [executado] |
| UI do chat | HUD próprio do Arthur (`arthur/arthur/static/index.html`) com o mapa do jogo num frame; o HUD do jogo fica igual. Alternativa disponível e não usada: painéis genéricos no HUD do jogo (`LiveServer.add_extension`) | **pronto** [executado] |
| Importar o fork | `arthur/arthur/bridge.py` — único ponto que põe o fork no `sys.path` e importa dele | **pronto** |

## Decisões da v1 (2026-10-21)

Regra: **o mais simples para começar.** Detalhes em `pendencias/projeto.md`.

- Reino fundado para Arthur no início; Arthur imortal; o reino não se divide nem se dissolve.
- Tudo no Gemini (`gemini-3.1-flash-lite`); `mock` para desenvolver e testar.
- Arthur obedece o mesmo interruptor de LLM das tribos e divide o mesmo teto de chamadas.
- Sem conhecimento limitado na v1: Arthur vê o relatório da própria tribo.
- O mundo segue no ritmo escolhido durante a conversa; conversa em português.
- **Arthur separado do jogo:** "Arthur" é o nome da parte do Thiago. Tem HUD e servidor próprios (mesmo processo, outra porta, mapa do jogo num frame); persona, conversa com o Gemini, memória e decisões ficam nele. Decisões do rei entram no mundo pelo formato que o jogo já valida (`TribePolicy`). (Revisado em 2026-10-21; antes: painel no HUD do jogo.)
- Mudanças no fork: preferir contornar por fora; gancho mínimo só se não houver jeito.

## Próximas etapas (proposta)

Cada etapa é pequena, testável offline com a mente `mock` e não muda a regressão do fork. Começa só quando o Thiago aprovar.

| # | Etapa | Pronto quando |
|---|---|---|
| 0 ✅ | **Decisões de produto** — tudo no mais simples, tudo no Gemini (ver abaixo) | feito em 2026-10-21 |
| 1 ✅ | **Esqueleto do Arthur** — `arthur/run.py` (jogo + Arthur), ponte de import, HUD e servidor próprios, conversa com respostas de teste; o fork ganhou, como recurso genérico opcional, painéis de extensão no HUD | feito em 2026-10-21: chat de ponta a ponta no navegador, `tests/arthur/test_server.py` passa, md5 intacto |
| 2 ✅ | **Reino do Arthur** — fundar o reino no início, Arthur chefe fixo, imortal, reino sem dividir; persona aplicada aos traços dele; **visível no mapa** (sprite de rei + plaquinha "Arthur", via "personagem destacado" genérico no fork) e botão "onde está o rei?" no HUD do Arthur | feito em 2026-10-21: `tests/arthur/test_kingdom.py` (anos de jogo, fome, ferimento, doença, Smite, colonos, divisão, vagas de LLM, reset), md5 intacto; visto no navegador |
| 3 | **Mente do Arthur** — a tribo dele decidida por um loop próprio (persona + contexto), demais tribos como hoje | políticas com justificativa, com `mock` e com Gemini |
| 4 | **Chat do conselheiro** — rota + UI; conselho vira item de agenda do próximo conselho | Arthur responde em personagem; pode recusar; o chat não muda o mundo diretamente |
| 5 | **Memória, confiança, conhecimento limitado** | conselhos e consequências lembrados; Arthur não sabe o que não viu |
| 6 | **Avaliação** pelos critérios da visão §11 | cenários roteirizados passam |

Design detalhado das etapas 3–5 (camadas de contexto, contratos de saída, confiança): `rascunhos/arthur-design.md` — revisar antes da etapa 3.

## Cuidados

- **Orçamento de LLM:** o plano grátis tem limite por minuto e por dia, e o Gemini oscila (503). Desenvolver com `mock`; com IA real, Arthur e tribos dividem o mesmo teto — talvez reduzir `max_minds` quando Arthur estiver ativo.
- **Segurança:** o chat não pode herdar os problemas do servidor do fork (CSRF, DNS rebinding).
- **Testes:** cenários por seed com `mock` são reprodutíveis; com LLM real, não.
