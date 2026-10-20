# llWorld

Protótipo de jogo: um mundo simulado que evolui sozinho, com personagens movidos por LLM. Primeiro recorte: o jogador como **conselheiro do Rei Arthur**, por chat — Arthur decide sozinho; o jogador influencia, não controla.

Princípio: **a simulação manda nas regras do mundo; a LLM propõe decisões de alto nível que o jogo valida e executa.** Nada narrado pode contradizer o estado da simulação.

## Fase atual

Documentação e preparação de ambiente (Python 3.10 em instalação; ajustes no terreno). **Não implementar o `worldbox-ai/` sem pedido explícito.**

## Camadas

- **`worldbox/`** — fork do jogo original, submódulo git (`thiagohila/worldbox`). "O jogo" = sempre este fork. Tratar como terceiros: não editar; se inevitável, mudança mínima e genérica, commitada no submódulo e depois o ponteiro no repo raiz.
- **`worldbox-ai/`** — camada própria do llWorld (ainda não existe). Usará o jogo só pela superfície pública dele.
- **`worldbox-clone-backup/`** — cópia não versionada do fork. Não editar nem commitar.

## Onde está o contexto

| Preciso de… | Ler |
|---|---|
| o que estamos construindo | `llWorld-visao-produto.md` |
| índice e convenções dos docs | `docs/README.md` |
| como o jogo funciona, por tema | `docs/worldbox/01..06-*.md` |
| rodar e testar | `docs/worldbox/05-executar-e-testar.md` |
| onde plugar código e problemas conhecidos | `docs/worldbox/06-extensao-e-armadilhas.md` |
| ideias (não aprovadas) para a IA | `docs/rascunhos/` |

Leia sob demanda; não carregue tudo.

## Agentes do projeto (`.claude/agents/`)

- **`worldbox-guide`** — somente leitura; responde dúvidas sobre o código do jogo e confere se os docs batem com o código.
- **`sim-runner`** — roda o jogo com segurança (headless, determinismo/md5, mapa ao vivo) e relata.

## Essenciais do ambiente

- Python 3.10+; o `python3` do pyenv (3.8) não funciona.
- Dentro de `worldbox/`: `PYTHONDONTWRITEBYTECODE=1 python3.10 -m worldbox.main --no-ai --days 3000 --seed 42`.
- Mapa ao vivo em `http://127.0.0.1:8765/` (não `localhost`: OrbStack usa a porta).
- Não há testes automatizados; regressão = md5 com mesmo seed, sem chaves de API no ambiente.

## Convenções

- Comunicação com o usuário e docs em português; código do fork em inglês.
- Docs marcam **[código]** / **[executado]** / **[hipótese]** e citam `arquivo.py:função`.
- Ao atualizar o submódulo, revisar `docs/worldbox/` e o hash de referência em `docs/README.md`.
