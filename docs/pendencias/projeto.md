# Pendências — projeto (llWorld)

Decisões, infraestrutura e tarefas do llWorld como um todo (fora do código do fork). Para problemas do jogo, ver `jogo.md`.

Formato: `- [ ] **título** — detalhe.` · Prioridade: 🔴 alta · 🟡 média · ⚪ baixa. Ao resolver, marque `[x]` e anote commit/data.

## Repositório e infraestrutura

- [x] 🟡 **Sem remote no repo llWorld** — resolvido em 2026-10-21: `origin` = `git@github.com:thiagohila/llWorld.git`, branch `main`.
- [x] 🟡 **README raiz desatualizado** — reescrito em 2026-10-21: origem do fork, estado atual, como rodar, links para visão, roadmap e `CLAUDE.md`.
- [ ] ⚪ **Acompanhar o upstream** — checar de tempos em tempos `git -C worldbox ls-remote upstream` e decidir se puxa mudanças de `ryfcx/worldbox`.
- [ ] ⚪ **Destino do `worldbox-clone-backup/`** — cópia idêntica do fork, hoje no `.gitignore`. Manter, mover para fora do repo ou apagar.
- [ ] ⚪ **`python3` global do pyenv quebrado** — 3.8.13 sem OpenSSL 1.1. O projeto usa a `.venv` (3.14), mas o global da máquina segue quebrado.

## Próxima fase — `worldbox-ai/` (ver `../roadmap.md`)

- [x] 🔴 **Etapa 0 — decisões de produto** — tudo na opção mais simples, tudo no Gemini (2026-10-21; ver seções abaixo).
- [ ] 🔴 **Etapa 1 — esqueleto do `worldbox-ai/`** — entrypoint com engine + runner + mapa do fork, ponte de import, config, testes offline.
- [ ] 🟡 **Etapa 2 — reino do Arthur** — fundar o reino, chefe fixo, persona.
- [ ] 🟡 **Etapa 3 — mente do Arthur** — loop próprio de decisão para a tribo dele; revisar antes o rascunho de design.
- [ ] 🟡 **Etapa 4 — chat do conselheiro** — rota segura + UI; conselho vira agenda, nunca muda o mundo direto.
- [ ] ⚪ **Etapa 5 — memória, confiança, conhecimento limitado.**
- [ ] ⚪ **Etapa 6 — avaliação pelos critérios da visão §11.**

## Decisões de arquitetura

Regra geral (Thiago, 2026-10-21): **tudo na opção mais simples para este início.** Revisitar só quando atrapalhar.

- [x] 🔴 **Estratégia para mudanças no fork** — preferir contornar por fora (patch/subclasse no `worldbox-ai`); gancho mínimo no fork só quando não houver outro jeito. 2026-10-21.
- [ ] 🟡 **Correções do fork (`jogo.md`)** — decidir caso a caso, quando cada uma atrapalhar a próxima etapa.
- [x] 🟡 **Como o `worldbox-ai/` importa o fork** — `sys.path` num único ponto do entrypoint. 2026-10-21.
- [ ] 🟡 **Rascunho de design da IA** — revisar `docs/rascunhos/worldbox-ai-design.md` antes da etapa 3, simplificando para a v1.

## Decisões de produto (protótipo do Arthur)

Decididas em 2026-10-21 pela regra "o mais simples" — ver `../roadmap.md`.

- [x] 🔴 **Origem do reino** — um reino fundado para Arthur no início do mundo (mesmo mecanismo do `/found`).
- [x] 🔴 **Morte de Arthur** — imortal no protótipo; sem sucessão.
- [x] 🔴 **Divisão e dissolução do reino** — o reino não se divide nem se dissolve.
- [x] 🟡 **Arthur e o interruptor de LLM** — obedece o mesmo controle das tribos: `--no-ai`, botão **AI**/tecla `M` e `ai off` param o Arthur também.
- [x] 🟡 **Conhecimento limitado** — fora da v1: Arthur vê o mesmo relatório que a mente da tribo dele receberia.
- [x] 🟡 **Ritmo do mundo vs. conversa** — o mundo segue no ritmo escolhido; o jogador pausa se quiser.
- [x] ⚪ **Idioma** — Arthur conversa em português (prompt e resposta); as mentes das tribos continuam como no fork.
- [x] ⚪ **Modelo de LLM** — tudo no Gemini (`gemini-3.1-flash-lite`, via `.env`); `mock` só para desenvolver e testar.
- [x] 🟡 **Orçamento de LLM com Arthur ativo** — um teto só, compartilhado entre Arthur e tribos (`MindDirector.call_cap`).
- [x] 🟡 **UI do chat** — painel de conversa no HUD do jogo, genérico (extensão registrada de fora); conversa, persona, chamadas de LLM e decisões ficam no `worldbox-ai`. Revisado em 2026-10-21 (antes: página própria).

## Qualidade e processo

- [ ] 🟡 **Estratégia de testes do `worldbox-ai/`** — padrão já provado no jogo: API simulada, `.env` isolado, mente `mock` para cenários por seed, regressão md5 do fork (`tests/worldbox/`). Aplicar o mesmo no `worldbox-ai`.
- [x] 🟡 **Testes offline fora do repo** — levados para `tests/worldbox/` (mentes, fontes de LLM, Smite) e `tools/perf/` (medições) em 2026-10-21.
- [ ] ⚪ **Script de regressão** — automatizar a checagem de md5 (`docs/worldbox/05-executar-e-testar.md`) junto com `tests/worldbox/` em um comando só.
- [ ] ⚪ **Manutenção dos docs** — ao atualizar o submódulo, revisar `docs/worldbox/` e o hash em `docs/README.md` e `docs/ambiente.md`.
