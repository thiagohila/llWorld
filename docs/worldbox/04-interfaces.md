# worldbox — interfaces

Nenhuma interface muda regras: todas leem o motor por `runner.lock`. As únicas que alteram estado são as ferramentas de deus e o controle de execução.

## Mapa ao vivo — `cli/webview.py` + `cli/static/live.html`

- **[código]** `LiveServer`: `ThreadingHTTPServer` em `127.0.0.1:8765` (tenta as 8 portas seguintes se ocupada). `LiveState` monta os JSONs sob lock.
- **[código]** Só `do_GET`, inclusive para rotas que alteram estado:

| Rota | Faz |
|---|---|
| `/` | página (`static/live.html`, relida do disco a cada request) |
| `/world` | terreno e dimensões, buscado uma vez |
| `/state?since=` | snapshot: agentes, tribos, mentes, assentamentos, log; polling a cada 500 ms |
| `/inspect?x=&y=` | detalhe de um tile |
| `/overlay?kind=` | camada (fertilidade etc.), a cada 4 s |
| `/explain` | narrador; **solta o lock antes da chamada de rede** |
| `/act?tool=&x=&y=&radius=` | ferramentas de deus (quebram determinismo) |
| `/found?x=&y=&name=&house=&people=` | planta uma civilização com provedor escolhido |
| `/control?action=&value=` | pause, resume, speed |

- **[executado]** Nesta máquina o OrbStack ocupa `*:8765`; `localhost` cai nele. Usar `127.0.0.1`.

## Terminal — `cli/terminal.py`, `cli/live.py`

- **[código]** REPL com comandos: `start`, `pause`, `step`, `advance <n>`, `reset`, `seed <n>`, `agent <id>`, `stats`, `tribes`, `tribe <id>`, `tech`, `wars`, `towns`, `chronicle`, `minds`, `narrate`, `export`, `view`, `livemap`, `events`, `help`, `exit`.
- **[código]** `start` abre o dashboard que se redesenha (`cli/live.py`).

## Viewer gravado — `export.py`, `tools/`

- **[código]** `RunRecorder` grava snapshots em `worldbox_run.json`; `tools/build_viewer.py` + `viewer_template.html` geram `worldbox.html` autônomo. `--view N` faz tudo e abre o navegador. Os dois arquivos são gitignored.
