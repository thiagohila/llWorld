"""Run the game with Arthur on top.

One process, two servers: the game's live map (its own HUD, unchanged) and
Arthur's HUD, which shows that map in a frame beside the conversation with
the king. From the llWorld root, with the venv active:

    python arthur/run.py                     # opens Arthur's HUD (http://127.0.0.1:8766/)
    python arthur/run.py --no-ai --seed 42
    python arthur/run.py --no-open --port 8765 --arthur-port 8766
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
import time
import webbrowser
from typing import List, Optional

from arthur.advisor import Advisor
from arthur.bridge import Config, LiveServer, SimulationEngine, SimulationRunner
from arthur.server import ArthurServer


def build(seed: Optional[int] = None, no_ai: bool = False, port: int = 8765, arthur_port: int = 8766):
    """The game (engine, runner, live map) and Arthur's server, not yet started."""
    config = Config()
    if no_ai:
        config = dataclasses.replace(config, ai=dataclasses.replace(config.ai, enabled=False))
    engine = SimulationEngine(config=config, seed=seed)
    runner = SimulationRunner(engine)
    game = LiveServer(engine, runner, port=port)
    advisor = Advisor(engine, runner)
    arthur = ArthurServer(engine, runner, advisor, game_url="", port=arthur_port)
    return engine, runner, game, arthur


def start(game: LiveServer, arthur: ArthurServer) -> None:
    """Start both servers; Arthur's page frames whatever URL the game got."""
    arthur.game_url = game.start()
    arthur.start()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="worldbox + Arthur")
    parser.add_argument("--seed", type=int, default=None, help="world seed")
    parser.add_argument("--no-ai", action="store_true", help="LLM minds off from the start")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    parser.add_argument("--port", type=int, default=8765, help="first port to try for the game's map")
    parser.add_argument("--arthur-port", type=int, default=8766, help="first port to try for Arthur's HUD")
    args = parser.parse_args(argv)

    engine, runner, game, arthur = build(args.seed, args.no_ai, args.port, args.arthur_port)
    try:
        start(game, arthur)
    except OSError as error:
        print(f"Could not start: {error}", file=sys.stderr)
        game.stop()
        return 1
    print(f"Game map:    {arthur.game_url}")
    print(f"Arthur's HUD: {arthur.url}")
    if not args.no_open:
        webbrowser.open(arthur.url)
    runner.set_delay(engine.config.simulation.autorun_tick_seconds)
    runner.start()
    print("Simulation running. Press Ctrl-C to stop.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        runner.pause()
        arthur.stop()
        game.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
