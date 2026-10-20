# worldbox — segurança

Revisão de 2026-10-20 sobre o fork em `4579b3c`. Nenhuma correção aplicada no fork; riscos registrados para decidir depois.

## Chaves e segredos

- **[executado]** Nenhuma chave real nos arquivos nem no histórico git (repo raiz, `worldbox/`, `worldbox-clone-backup/`). Só o placeholder `DEEPSEEK_API_KEY=your-key-here` no README do fork e `.env.example` com valores vazios.
- **[executado]** Nenhum `.env` existe hoje; nenhuma chave exportada no shell nem nos profiles (`~/.zshrc` etc.).
- **[código]** `.env` está no `.gitignore` do fork e da raiz.
- **[código]** As chaves só saem da máquina no header `Authorization` para os endpoints oficiais, sempre com TLS verificado (`ai/client.py:chat`, `ssl_context`).
- **[código]** As respostas JSON do servidor só citam o *nome* da variável (`"key": "DEEPSEEK_API_KEY"`), nunca o valor.
- **[código]** Atenção: `load_dotenv` procura `.env` na raiz do fork **e em todos os diretórios acima do cwd**. Um `.env` esquecido em `~/Documents` ou `~` seria carregado. Hoje não há nenhum **[executado]**.
- **[hipótese]** Erros da API são repassados com até 300 caracteres do corpo da resposta (`chat`, `detail[:300]`) e aparecem no painel Minds. Provedores costumam mascarar a chave em erros 401, mas não é garantido.

## Servidor do mapa ao vivo (`cli/webview.py`)

Escuta só em `127.0.0.1` **[código]** — não é exposto na rede. Os riscos vêm do navegador do próprio usuário:

| Risco | Evidência | Impacto |
|---|---|---|
| **CSRF**: rotas que alteram estado são GET, sem checagem de `Origin`/token | **[executado]** `/act?tool=plague` com `Origin: https://site-malicioso.example` foi aceito | qualquer site aberto no navegador enquanto o mapa roda pode disparar ferramentas de deus, fundar civilizações (`/found`), pausar, e chamar `/explain` (gasta créditos de API) |
| **DNS rebinding**: `Host` não é validado | **[executado]** `Host: evil.example:8765` respondeu 200 | um site pode ler `/state` (estado do mundo, erros da API) |
| **Travamento por raio**: `radius` de `/act` não tem limite | **[código]** `tiles_within` itera `(2r+1)` por linha válida, segurando `runner.lock` | um `radius` enorme congela a simulação |
| Erros 500 com texto da exceção | **[código]** `send_error(500, str(error))` | vazamento menor de detalhes internos |

- **[código]** XSS: o front usa `esc()` em todo texto vindo de LLM ou nomes de tribo antes de `innerHTML`. `esc` não escapa aspas, mas os únicos usos em atributo recebem dados do servidor, não da LLM. Sem achado.
- **[código]** Nome de civilização em `/found` é filtrado para alfanuméricos e ` -'` (máx. 40) antes de ir para o prompt.

## Mitigações possíveis (não aplicadas)

- Uso imediato: não deixar o mapa ao vivo aberto enquanto navega em sites não confiáveis, especialmente com chaves configuradas; preferir `--no-ai` quando não precisar das mentes.
- No fork (se decidirmos editá-lo): validar `Host` ∈ {`127.0.0.1:porta`, `localhost:porta`}, exigir um token por sessão nas rotas que alteram estado (ou POST + checagem de `Origin`), limitar `radius`, e responder 500 sem o texto da exceção.
- No `worldbox-ai/`: qualquer servidor próprio deve nascer com essas proteções.
