# Documentação do llWorld

Índice e convenções. Leia só o que a tarefa precisa.

## Produto

- `../llWorld-visao-produto.md` — visão de produto: o que queremos construir e por quê. Fonte de verdade sobre o *quê*.

## Ambiente

- `ambiente.md` — versões de tudo que o projeto usa (Python, git, fork, modelos de LLM, portas) e como montar do zero.

## Referência do jogo (fork `worldbox/`)

| Arquivo | Quando ler |
|---|---|
| `worldbox/01-visao-geral.md` | primeiro contato; mapa de módulos, ciclo do dia, glossário |
| `worldbox/02-simulacao.md` | agentes, tribos, sociedade, diplomacia, eventos e crônica |
| `worldbox/03-ia.md` | cliente LLM, mentes das tribos, invenções, narrador, validação e falhas |
| `worldbox/04-interfaces.md` | mapa ao vivo (HTTP), terminal, viewer gravado |
| `worldbox/05-executar-e-testar.md` | ambiente, comandos, determinismo, regressão |
| `worldbox/06-extensao-e-armadilhas.md` | onde plugar código sem editar o fork; problemas conhecidos |
| `worldbox/07-seguranca.md` | chaves/segredos, riscos do servidor local, mitigações |
| `worldbox/08-performance.md` | custo por dia vs população, gargalos, velocidade real, front-end |

## Pendências (checklists)

- `pendencias/jogo.md` — bugs, riscos e limitações do fork.
- `pendencias/projeto.md` — decisões, infraestrutura e tarefas do llWorld.

## Rascunhos

- `rascunhos/worldbox-ai-design.md` — ideias antecipadas para a camada de IA. **Não aprovado.**

## Convenções destes docs

- Marcação de confiança: **[código]** lido no fonte · **[executado]** verificado rodando · **[hipótese]** não verificado.
- Referências como `arquivo.py:função`, relativas a `worldbox/worldbox/` (o pacote) salvo indicação.
- A referência descreve o fork no commit **`bfe84cd`** (upstream `4579b3c` + HUD/sprites `b10f9fb` + performance `bfe84cd`). Ao atualizar o submódulo, revisar os docs afetados e atualizar este hash.
- Docs curtos e por tema. Detalhe que só o código responde fica no código; aqui vai o mapa.
