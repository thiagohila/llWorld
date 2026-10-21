# Pendências — projeto (llWorld)

Decisões, infraestrutura e tarefas do llWorld como um todo (fora do código do fork). Para problemas do jogo, ver `jogo.md`.

Formato: `- [ ] **título** — detalhe.` · Prioridade: 🔴 alta · 🟡 média · ⚪ baixa. Ao resolver, marque `[x]` e anote commit/data.

## Repositório e infraestrutura

- [x] 🟡 **Sem remote no repo llWorld** — resolvido em 2026-10-21: `origin` = `git@github.com:thiagohila/llWorld.git`, branch `main`.
- [ ] 🟡 **README raiz desatualizado** — cita `worldbox-ai/` como existente, chama o fork de "upstream-derived game" sem dizer que é `ryfcx/worldbox` (e não o WorldBox comercial), e não aponta para `CLAUDE.md`, visão de produto nem `docs/`.
- [ ] ⚪ **Acompanhar o upstream** — checar de tempos em tempos `git -C worldbox ls-remote upstream` e decidir se puxa mudanças de `ryfcx/worldbox`.
- [ ] ⚪ **Destino do `worldbox-clone-backup/`** — cópia idêntica do fork, hoje no `.gitignore`. Manter, mover para fora do repo ou apagar.
- [ ] ⚪ **`python3` global do pyenv quebrado** — 3.8.13 sem OpenSSL 1.1. O projeto usa a `.venv` (3.14), mas o global da máquina segue quebrado.

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
- [ ] ⚪ **Modelo de LLM** — mesmo do fork (`deepseek-flash`) ou um mais capaz para a conversa.

## Qualidade e processo

- [ ] 🟡 **Estratégia de testes do `worldbox-ai/`** — unitários sem rede (provedor LLM falso), cenários por seed, regressão md5 do fork.
- [ ] ⚪ **Script de regressão** — automatizar a checagem de md5 (`docs/worldbox/05-executar-e-testar.md`) em vez de comando manual.
- [ ] ⚪ **Manutenção dos docs** — ao atualizar o submódulo, revisar `docs/worldbox/` e o hash em `docs/README.md` e `docs/ambiente.md`.
