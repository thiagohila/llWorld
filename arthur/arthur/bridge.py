"""The one place Arthur reaches into the game.

The fork is a git submodule at ``<llWorld>/worldbox`` and is not installable,
so its root goes on ``sys.path`` here, once. Everything else in Arthur
imports game types from this module, which keeps the dependency on the game
in a single, greppable spot.
"""

from __future__ import annotations

import sys
from pathlib import Path

FORK_ROOT = Path(__file__).resolve().parents[2] / "worldbox"


def ensure_fork_importable() -> None:
    """Put the fork on the import path, or explain how to fetch it."""
    if not (FORK_ROOT / "worldbox" / "__init__.py").is_file():
        raise RuntimeError(
            f"The worldbox game was not found at {FORK_ROOT}. "
            "Run `git submodule update --init` in the llWorld repo."
        )
    root = str(FORK_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


ensure_fork_importable()

from worldbox.agents.needs import Needs  # noqa: E402
from worldbox.ai import narrator  # noqa: E402
from worldbox.ai.client import all_houses, available_houses  # noqa: E402
from worldbox.ai.client import is_available as llm_available  # noqa: E402
from worldbox.cli.webview import LiveServer  # noqa: E402
from worldbox.config import Config  # noqa: E402
from worldbox.simulation.engine import SimulationEngine, SimulationRunner  # noqa: E402
from worldbox.simulation.events import EventKind  # noqa: E402
from worldbox.society import culture  # noqa: E402
from worldbox.society.epidemics import DISEASES  # noqa: E402
from worldbox.society.founding import found_tribe, settle_people  # noqa: E402
from worldbox.society.groups import GroupRegistry  # noqa: E402

__all__ = [
    "DISEASES", "FORK_ROOT", "Config", "EventKind", "GroupRegistry", "LiveServer", "Needs",
    "SimulationEngine", "SimulationRunner", "all_houses", "available_houses", "culture",
    "found_tribe", "llm_available", "narrator", "settle_people",
]
