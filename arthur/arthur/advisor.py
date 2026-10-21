"""The conversation between the player and King Arthur.

Arthur's own HUD and server (``arthur.server``) talk to this object; it also
speaks the game's generic extension protocol (``describe`` / ``handle``), so
it could be shown inside the game's HUD too, but Arthur does not do that.

Stage 1 (docs/roadmap.md) is the plumbing only: replies come from an offline
stand-in, so the whole path -- Arthur's HUD, its guarded server, this object
-- is proven without spending any LLM calls. Arthur's persona, Gemini and his
decisions replace ``placeholder_reply`` in later stages.

Rules this extension keeps from the start:

* the chat never changes the world; it only reads a little of it;
* it obeys the game's LLM switch (``engine.minds.paused``);
* replies are worked out on their own thread, so neither the HTTP request
  nor the simulation waits for them.
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional

MAX_TEXT = 600
MAX_HISTORY = 200

Reply = Callable[[str, Dict[str, Any]], str]


@dataclass
class Message:
    """One line of the conversation, as the HUD renders it."""

    id: int
    role: str  # "player", "character" or "system"
    text: str
    name: str = ""
    day: Optional[int] = None
    pending: bool = False


def placeholder_reply(text: str, context: Dict[str, Any]) -> str:
    """Stage 1 stand-in for Arthur: proves the round trip, decides nothing."""
    quoted = text if len(text) <= 80 else text[:77] + "..."
    return (
        f"(teste) Ouvi seu conselho: “{quoted}”. "
        f"Estamos no ano {context['year']}, com {context['population']} almas no mundo "
        f"e {context['tribes']} tribos. Ainda não governo reino algum — "
        "esta é só a etapa 1, sem LLM."
    )


class Advisor:
    """The conversation with the king, answered by ``reply``."""

    id = "advisor"

    def __init__(
        self,
        engine: Any,
        runner: Any,
        reply: Optional[Reply] = None,
        character: str = "Arthur",
    ) -> None:
        self.engine = engine
        self.runner = runner
        self.character = character
        self._reply = reply or placeholder_reply
        self._messages: List[Message] = []
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._busy = False
        # Arthur's own switch for this purpose; the game's switch still wins.
        self.llm_enabled = True
        # What answers the king, for the LLMs tab. A real backend sets
        # ``uses_llm`` and ``model`` on its reply function.
        self.uses_llm = bool(getattr(self._reply, "uses_llm", False))
        self.model = str(getattr(self._reply, "model", "") or "resposta de teste (sem LLM)")
        self.usage: Dict[str, int] = {
            "messages": 0, "replies": 0, "llm_calls": 0, "failures": 0,
            "tokens_in": 0, "tokens_out": 0,
        }
        self._add("system", "Etapa 1: o canal de conversa funciona; o Arthur de verdade chega nas próximas etapas.")

    # -- protocol (Arthur's server; also the game's extension protocol)

    def describe(self) -> Dict[str, Any]:
        return {
            "title": "Advisor",
            "kind": "chat",
            "subtitle": "Converse com o Rei Arthur. Ele ouve, mas decide sozinho.",
            "placeholder": "Aconselhe o rei…",
            "maxLength": MAX_TEXT,
        }

    def handle(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if action == "messages":
            return self._messages_since(payload.get("since"))
        if action == "send":
            return self._send(payload.get("text"))
        return {"ok": False, "error": f"Unknown action '{action}'."}

    def usage_snapshot(self) -> Dict[str, Any]:
        """This purpose's use, for Arthur's LLMs tab."""
        with self._lock:
            row: Dict[str, Any] = dict(self.usage)
            row["busy"] = self._busy
        row.update({"enabled": self.llm_enabled, "uses_llm": self.uses_llm, "model": self.model})
        return row

    # -- internals -------------------------------------------------------------

    def _add(self, role: str, text: str, **fields: Any) -> Message:
        with self._lock:
            message = Message(id=next(self._ids), role=role, text=text, **fields)
            self._messages.append(message)
            del self._messages[:-MAX_HISTORY]
            return message

    def _messages_since(self, since: Any) -> Dict[str, Any]:
        try:
            after = int(since)
        except (TypeError, ValueError):
            after = -1
        with self._lock:
            rows = [asdict(m) for m in self._messages if m.id > after]
            busy = self._busy
        return {"ok": True, "messages": rows, "thinking": busy}

    def _context(self) -> Dict[str, Any]:
        """The little the stand-in reads from the world, under the game's lock."""
        with self.runner.lock:
            engine = self.engine
            return {
                "day": engine.clock.day,
                "year": engine.clock.year,
                "population": len(engine.agents),
                "tribes": len(engine.groups.active()),
            }

    def _send(self, raw: Any) -> Dict[str, Any]:
        text = str(raw or "").strip()[:MAX_TEXT]
        if not text:
            return {"ok": False, "error": "Mensagem vazia."}
        with self._lock:
            if self._busy:
                return {"ok": False, "error": f"{self.character} ainda está respondendo."}
            self._busy = True
        context = self._context()
        self._add("player", text, name="Você", day=context["day"])
        with self._lock:
            self.usage["messages"] += 1
        silent = None
        if self.engine.minds.paused:
            # The game's LLM switch is off: Arthur stays silent too.
            silent = "As chamadas de LLM estão desligadas (botão AI). Ligue para o rei responder."
        elif not self.llm_enabled:
            silent = "A conversa do Arthur está desligada na aba LLMs. Ligue para o rei responder."
        if silent:
            self._add("system", silent)
            with self._lock:
                self._busy = False
            return {"ok": True}
        pending = self._add("character", "", name=self.character, day=context["day"], pending=True)
        threading.Thread(
            target=self._answer, args=(pending.id, text, context),
            name="llworld-advisor", daemon=True,
        ).start()
        return {"ok": True}

    def _answer(self, message_id: int, text: str, context: Dict[str, Any]) -> None:
        failed = False
        try:
            reply = self._reply(text, context)
            role, body = "character", str(reply or "").strip() or "…"
        except Exception as error:  # A failed reply must not wedge the panel.
            failed = True
            role, body = "system", f"{self.character} não conseguiu responder ({type(error).__name__})."
        with self._lock:
            self.usage["replies"] += 0 if failed else 1
            self.usage["failures"] += 1 if failed else 0
            if self.uses_llm:
                self.usage["llm_calls"] += 1
            for message in self._messages:
                if message.id == message_id:
                    message.role, message.text, message.pending = role, body, False
                    break
            self._busy = False
