"""Arthur: llWorld's own layer on top of the worldbox game.

The player is King Arthur's advisor. The game (the ``worldbox`` fork) owns
the world and its rules; Arthur owns its own HUD and server, the
conversation, the persona, the LLM calls and the king's decisions. It uses
only the game's public interfaces, all reached through ``bridge``, and the
game never imports anything from here. Plan: ``docs/roadmap.md``.
"""

__version__ = "0.1.0"
