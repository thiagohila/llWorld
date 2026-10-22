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
  (http://127.0.0.1:8766/, with the game map framed beside it), built on the
  game's public interfaces. Arthur's kingdom is founded on day zero; he is its
  fixed, immortal king and decides its policy with an LLM (Gemini), with a
  rationale you can read. Run `python arthur/run.py`.
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

With Arthur (from the llWorld root): `python arthur/run.py` opens his HUD;
`--no-ai` keeps every LLM off.

## Status

Experimental. The game is stable. Arthur: kingdom and the king's own
decisions work (stages 1–3); talking to him for real is stage 4. Plan in
`docs/roadmap.md`.
