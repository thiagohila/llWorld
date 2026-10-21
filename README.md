# llWorld

A world that does not wait for the player: an autonomous civilisation
simulation where AI-driven characters live, decide and change history. The
first prototype puts the player in the role of **King Arthur's advisor** —
Arthur listens, but decides for himself.

## Components

- `worldbox/` — the game: a git submodule with our fork of
  [ryfcx/worldbox](https://github.com/ryfcx/worldbox), a Python civilisation
  simulator (not the commercial *WorldBox – God Simulator*). Runs as it came,
  with a new HUD and art, performance work, and LLM tribe minds that can use
  free providers (Gemini, Groq, OpenRouter, a local Ollama) or an offline mock.
- `arthur/` — **Arthur**, the advisor layer: its own HUD and server
  (http://127.0.0.1:8766/, with the game map framed beside the conversation),
  built on the game's public interfaces. Run `python arthur/run.py`.
- `docs/` — reference for the fork, environment, security, performance,
  checklists and the roadmap.

## Start here

- `llWorld-visao-produto.md` — product vision (Portuguese).
- `docs/roadmap.md` — current state, layer interfaces, next steps.
- `CLAUDE.md` — working guide for this repo.

## Run the game

```bash
git clone --recursive git@github.com:thiagohila/llWorld.git && cd llWorld
python3.14 -m venv .venv && source .venv/bin/activate   # any Python 3.10+
cd worldbox
python -m worldbox.main --live --no-ai     # live map at http://127.0.0.1:8765/
```

LLM minds: copy `worldbox/.env.example` to `worldbox/.env` and fill one source.

## Status

Experimental. The game is stable; the advisor layer is the next phase.
