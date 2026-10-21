# worldbox — interfaces

Nenhuma interface muda regras: todas leem o motor por `runner.lock`. As únicas que alteram estado são as ferramentas de deus e o controle de execução.

## Mapa ao vivo — `cli/webview.py` + `cli/static/live.html`

- **[código]** `LiveServer`: `ThreadingHTTPServer` em `127.0.0.1:8765` (tenta as 8 portas seguintes se ocupada). `LiveState` monta os JSONs sob lock.
- **[código]** Só `do_GET`, inclusive para rotas que alteram estado:

| Rota | Faz |
|---|---|
| `/` | página (`static/live.html`, relida do disco a cada request) |
| `/world` | terreno e dimensões, buscado uma vez |
| `/state?since=` | snapshot: agentes, tribos, mentes, assentamentos, log; `ai.usage` = chamadas, por minuto/teto, puladas, falhas, tokens, `halted`; polling a cada 500 ms |
| `/inspect?x=&y=` | detalhe de um tile |
| `/overlay?kind=` | camada (fertilidade etc.), a cada 4 s |
| `/explain` | narrador; **solta o lock antes da chamada de rede** |
| `/act?tool=&x=&y=&radius=` | ferramentas de deus (quebram determinismo); responde `affected`. Smite mata na hora (desde `d6472e1`) |
| `/found?x=&y=&name=&house=&people=` | planta uma civilização com provedor escolhido |
| `/control?action=&value=` | pause, resume, speed; `ai` (on/off/toggle), `ai_cap` (N ou vazio), `ai_forget` — ver `03-ia.md` → Controle em tempo real. Responde `aiPaused` e `aiCap` |
| `/sprites/<arquivo>` | spritesheets e `sprites.json` de `static/sprites/`; só nomes simples `.png`/`.json` (sem `..`), lidos do disco a cada request |

- **[executado]** Nesta máquina o OrbStack ocupa `*:8765`; `localhost` cai nele. Usar `127.0.0.1`.

### HUD (redesenhado em 2026-10-20, só front-end em `static/live.html`)

- Topo: data/era, chips de status com ícone (população com tendência anual, civs, assentamentos, tecnologias, guerras e doentes com alerta), medidor de comida, play/pause, velocidade, zoom.
- Esquerda: barra de ícones (camadas e poderes) + gaveta contextual com descrição, raio e formulário de fundação. Prévia do raio no mapa.
- Direita: abas Inspect / Civs / Minds / Tech / History. Embaixo: log com filtros (Life desligado por padrão), toasts para guerras, pragas, invenções e marcos, minimapa clicável.
- Sprites em pixel art gerados no navegador: terreno pré-renderizado (8 px por tile, 2 quadros de animação), pessoas 9×11 por profissão/estado, prédios por nível (Camp → City), placas de nome.
- **Arte desenhada (2026-10-21):** spritesheets do Claude Design em `cli/static/sprites/` (`people`, `overlays`, `buildings`, `terrain`, `props` + `sprites.json` com células e âncoras). A página troca, pixel a pixel, o magenta (`#FF00FF`/`#FF80FF`/`#A000A0`) pela cor da tribo e pele/cabelo neutros pela variação da tribo; usa quadros de andar só para quem se moveu; árvores e efeitos dos poderes vêm de `props`. Praias e espuma continuam geradas por código (os tiles não têm transições). Sem os arquivos, cai nos sprites gerados. Trocar a arte = substituir os arquivos e dar F5.
- Ao carregar, a página envia ao servidor a velocidade destacada (1×), para não rodar no default de 0,12 s do `config.py`.
- Botão **AI on/off** no topo (ao lado do play) e controles de LLM na aba Minds (ligar/desligar, teto por minuto, esquecer decisões).
- Atalhos: `Espaço` pausa · `M` liga/desliga LLM · `1`–`6` poderes · `N` fundar · `L` alterna camadas · `F` enquadrar · `+`/`-` zoom · `[`/`]` velocidade · `Esc` cancela.

## Terminal — `cli/terminal.py`, `cli/live.py`

- **[código]** REPL com comandos: `start`, `pause`, `step`, `advance <n>`, `reset`, `seed <n>`, `agent <id>`, `stats`, `tribes`, `tribe <id>`, `tech`, `wars`, `towns`, `chronicle`, `minds`, `ai [on|off|cap N|forget]`, `narrate`, `export`, `view`, `livemap`, `events`, `help`, `exit`.
- **[código]** `start` abre o dashboard que se redesenha (`cli/live.py`).

## Viewer gravado — `export.py`, `tools/`

- **[código]** `RunRecorder` grava snapshots em `worldbox_run.json`; `tools/build_viewer.py` + `viewer_template.html` geram `worldbox.html` autônomo. `--view N` faz tudo e abre o navegador. Os dois arquivos são gitignored.
