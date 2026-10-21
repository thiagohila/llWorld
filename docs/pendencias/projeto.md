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

- [ ] 🔴 **Etapa 0 — decisões de produto** — itens da seção "Decisões de produto" abaixo.
- [ ] 🔴 **Etapa 1 — esqueleto do `worldbox-ai/`** — entrypoint com engine + runner + mapa do fork, ponte de import, config, testes offline.
- [ ] 🟡 **Etapa 2 — reino do Arthur** — fundar o reino, chefe fixo, persona.
- [ ] 🟡 **Etapa 3 — mente do Arthur** — loop próprio de decisão para a tribo dele; revisar antes o rascunho de design.
- [ ] 🟡 **Etapa 4 — chat do conselheiro** — rota segura + UI; conselho vira agenda, nunca muda o mundo direto.
- [ ] ⚪ **Etapa 5 — memória, confiança, conhecimento limitado.**
- [ ] ⚪ **Etapa 6 — avaliação pelos critérios da visão §11.**

## Decisões de arquitetura

- [ ] 🔴 **Estratégia para mudanças no fork** — quando um gancho for inevitável (ex.: líder fixo), patch por fora vs. commit mínimo no submódulo. Definir critério.
- [ ] 🟡 **Correções do fork (`jogo.md`)** — decidir quais corrigir no fork, quais contornar no `worldbox-ai/` e quais aceitar.
- [ ] 🟡 **Como o `worldbox-ai/` importa o fork** — `sys.path` no entrypoint, `PYTHONPATH` ou tornar o fork instalável.
- [ ] 🟡 **Rascunho de design da IA** — revisar `docs/rascunhos/worldbox-ai-design.md`: aprovar, ajustar ou descartar.

## Decisões de produto (protótipo do Arthur)

Vindas da visão (`llWorld-visao-produto.md`) e do rascunho de design.

- [ ] 🔴 **Origem do reino** — tribo fundada para Arthur no início ou tribo existente que ele assume.
- [ ] 🔴 **Morte de Arthur** — imortal no protótipo ou sucessão como mecânica.
- [ ] 🔴 **Divisão e dissolução do reino** — qual grupo continua sendo "o reino" ao dividir (>55) ou dissolver (<4); bloquear?
- [ ] 🟡 **Arthur e o `--no-ai`** — desligar Arthur junto com as mentes ou mantê-lo independente.
- [ ] 🟡 **Conhecimento limitado** — raio de contato, atraso de notícias, informações falsas.
- [ ] 🟡 **Ritmo do mundo vs. conversa** — o mundo pausa, desacelera ou segue enquanto o jogador conversa.
- [ ] ⚪ **Idioma** — Arthur fala português; prompts internos em inglês ou português.
- [ ] ⚪ **Modelo de LLM** — hoje as tribos usam Gemini grátis (`gemini-3.1-flash-lite`); decidir se Arthur usa o mesmo, um mais capaz para a conversa, ou `mock` em desenvolvimento.
- [ ] 🟡 **Orçamento de LLM com Arthur ativo** — Arthur e tribos dividem o mesmo teto grátis (por minuto e por dia); talvez reduzir `max_minds` ou dar prioridade ao Arthur.
- [ ] 🟡 **UI do chat** — página própria do `worldbox-ai` ou painel no `live.html` do fork.

## Qualidade e processo

- [ ] 🟡 **Estratégia de testes do `worldbox-ai/`** — padrão já provado no jogo: API simulada, `.env` isolado, mente `mock` para cenários por seed, regressão md5 do fork (`tests/worldbox/`). Aplicar o mesmo no `worldbox-ai`.
- [x] 🟡 **Testes offline fora do repo** — levados para `tests/worldbox/` (mentes, fontes de LLM, Smite) e `tools/perf/` (medições) em 2026-10-21.
- [ ] ⚪ **Script de regressão** — automatizar a checagem de md5 (`docs/worldbox/05-executar-e-testar.md`) junto com `tests/worldbox/` em um comando só.
- [ ] ⚪ **Manutenção dos docs** — ao atualizar o submódulo, revisar `docs/worldbox/` e o hash em `docs/README.md` e `docs/ambiente.md`.
