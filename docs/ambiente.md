# Ambiente e versões

Fonte única das versões do projeto. Atualize aqui quando algo mudar e registre a data.

Última verificação: **2026-10-20**, na máquina de desenvolvimento do Thiago.

## Requisitos

| Item | Versão usada | Mínimo / observação |
|---|---|---|
| **Python** | **3.14.6** (Homebrew), na `.venv` da raiz | 3.10+ (exigência do fork). Testado também em 3.10.15 e 3.12.15 com resultado idêntico |
| Pacotes Python | nenhum — só stdlib (`pip 26.1.2` na venv) | `certifi` opcional: usado só se o Python não tiver CAs do sistema (`ai/client.py:ssl_context`). **Não necessário aqui**: a venv carrega 188 CAs de `/usr/local/etc/openssl@3/cert.pem` e o TLS 1.3 com `api.deepseek.com` e `api.openai.com` foi verificado |
| OpenSSL (do Python) | 3.5.9 | necessário só para chamar as APIs de LLM (HTTPS) |
| git | 2.51.0 | precisa de suporte a submódulos |
| SO | macOS 26.5.2 (x86_64) | o dashboard do terminal usa `termios`/`tty` → macOS/Linux. Headless e mapa ao vivo não dependem disso |
| Navegador | qualquer moderno | mapa ao vivo e viewer são HTML+JS estáticos, sem CDN externo |
| Homebrew | 7.0.10 | origem dos Pythons em `/usr/local/bin/python3.x` |

**Não usar:** o `python3` global do pyenv (3.8.13) — quebra ao importar `ssl` (falta OpenSSL 1.1) e é abaixo do mínimo.

## Código

| Item | Versão |
|---|---|
| Fork `worldbox/` (submódulo) | `bfe84cd` (2026-10-21; 2 commits à frente do upstream), `git@github.com:thiagohila/worldbox.git`, branch `main`; versão do pacote `0.1.0` |
| Upstream do fork | `https://github.com/ryfcx/worldbox` (remote `upstream` no submódulo) — mesmo commit `4579b3c` em 2026-10-20 |
| Docs de referência do fork | descrevem `bfe84cd` |
| `worldbox-ai/` | ainda não existe |

## Serviços externos (opcionais)

Só usados com IA ligada (sem `--no-ai` e com chave em `worldbox/.env`). Definidos em `worldbox/worldbox/ai/client.py:HOUSES`.

| Provedor | Modelo | Endpoint | Variável |
|---|---|---|---|
| DeepSeek | `deepseek-flash` | `https://api.deepseek.com/chat/completions` | `DEEPSEEK_API_KEY` |
| OpenAI | `gpt-5-mini` | `https://api.openai.com/v1/chat/completions` | `OPENAI_API_KEY` |

O narrador só funciona com a chave DeepSeek (ver `worldbox/06-extensao-e-armadilhas.md`).

## Portas locais

| Porta | Uso |
|---|---|
| `127.0.0.1:8765` | mapa ao vivo (tenta até 8772 se ocupada) |
| `*:8765` | também ocupada pelo OrbStack nesta máquina → acessar por `127.0.0.1`, não `localhost` |

## Montar do zero

```bash
git clone <llWorld> && cd llWorld
git submodule update --init           # traz o fork em worldbox/
python3.14 -m venv .venv               # ou qualquer Python 3.10+
source .venv/bin/activate
cd worldbox
cp .env.example .env                   # opcional: chaves de LLM
PYTHONDONTWRITEBYTECODE=1 python -m worldbox.main --no-ai --days 3000 --seed 42 | md5
# esperado: 46183c8d284315695c7706c0f923745a (sem chaves no ambiente)
```

## Verificar versões

```bash
.venv/bin/python --version
.venv/bin/python -c "import ssl; print(ssl.OPENSSL_VERSION)"
git --version
git -C worldbox log -1 --format='%h %ad' --date=short
```
