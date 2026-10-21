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

### HUD (redesenhado em 2026-10-20, só front-end em `static/live.html`)

- Topo: data/era, chips de status com ícone (população com tendência anual, civs, assentamentos, tecnologias, guerras e doentes com alerta), medidor de comida, play/pause, velocidade, zoom.
- Esquerda: barra de ícones (camadas e poderes) + gaveta contextual com descrição, raio e formulário de fundação. Prévia do raio no mapa.
- Direita: abas Inspect / Civs / Minds / Tech / History. Embaixo: log com filtros (Life desligado por padrão), toasts para guerras, pragas, invenções e marcos, minimapa clicável.
- Sprites em pixel art gerados no navegador: terreno pré-renderizado (8 px por tile, 2 quadros de animação), pessoas 9×11 por profissão/estado, prédios por nível (Camp → City), placas de nome.
- Atalhos: `Espaço` pausa · `1`–`6` poderes · `N` fundar · `L` alterna camadas · `F` enquadrar · `+`/`-` zoom · `[`/`]` velocidade · `Esc` cancela.

## Terminal — `cli/terminal.py`, `cli/live.py`

- **[código]** REPL com comandos: `start`, `pause`, `step`, `advance <n>`, `reset`, `seed <n>`, `agent <id>`, `stats`, `tribes`, `tribe <id>`, `tech`, `wars`, `towns`, `chronicle`, `minds`, `narrate`, `export`, `view`, `livemap`, `events`, `help`, `exit`.
- **[código]** `start` abre o dashboard que se redesenha (`cli/live.py`).

## Viewer gravado — `export.py`, `tools/`

- **[código]** `RunRecorder` grava snapshots em `worldbox_run.json`; `tools/build_viewer.py` + `viewer_template.html` geram `worldbox.html` autônomo. `--view N` faz tudo e abre o navegador. Os dois arquivos são gitignored.
