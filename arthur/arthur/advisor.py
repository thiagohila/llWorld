"""The conversation between the player and King Arthur.

Arthur's own HUD and server (``arthur.server``) talk to this object; it also
speaks the game's generic extension protocol (``describe`` / ``handle``), so
it could be shown inside the game's HUD too, but Arthur does not do that.

The king answers through ``voice`` (``voice.KingVoice``, stage 4a): his
persona, his realm's report, his recent decisions and the last exchanges,
through the council's LLM source. Without an LLM (``--no-ai``, no source, or
no voice given) an offline stand-in answers, so the whole path -- Arthur's
HUD, its guarded server, this object -- still works without any calls.

Rules this extension keeps from the start:

* the chat never changes the world; it only reads a little of it;
* it obeys the game's LLM switch (``engine.minds.paused``), its own switch,
  the per-minute budget and the quota gate;
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
    advice: Optional[Dict[str, Any]] = None  # the king's reading of the advice, if any


def placeholder_reply(text: str, context: Dict[str, Any]) -> str:
    """Stand-in reply when no LLM can answer: proves the round trip, says
    nothing it does not know."""
    quoted = text if len(text) <= 80 else text[:77] + "..."
    return (
        f"(sem LLM) Ouvi seu conselho: “{quoted}”. "
        f"Estamos no ano {context['year']}, com {context['population']} almas no mundo "
        f"e {context['tribes']} tribos. Para conversar de verdade preciso de uma LLM "
        "(rodar sem --no-ai, com uma fonte no .env)."
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
        voice: Optional[Any] = None,
    ) -> None:
        self.engine = engine
        self.runner = runner
        self.character = character
        self._reply = reply or placeholder_reply
        self.voice = voice
        self._messages: List[Message] = []
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._busy = False
        # Arthur's own switch for this purpose; the game's switch still wins.
        self.llm_enabled = True
        self.usage: Dict[str, int] = {
            "messages": 0, "replies": 0, "llm_calls": 0, "failures": 0,
            "tokens_in": 0, "tokens_out": 0,
        }
        if self._live():
            self._add("system", "Fale com o Rei Arthur. Ele ouve e responde, mas decide sozinho, "
                                "no conselho dele (aba Decisões).")
        else:
            self._add("system", "Sem LLM: o rei responde com um texto de teste. "
                                "As decisões dele estão na aba Decisões.")

    @property
    def uses_llm(self) -> bool:
        return self._live()

    @property
    def model(self) -> str:
        return self.voice.model if self._live() else "resposta de teste (sem LLM)"

    def _live(self) -> bool:
        return self.voice is not None and self.voice.live()

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

    def _context(self, live: bool) -> Dict[str, Any]:
        """What the reply reads from the world, under the game's lock. A live
        voice also takes the conversation so far and its share of the budget."""
        with self.runner.lock:
            engine = self.engine
            context: Dict[str, Any] = {
                "day": engine.clock.day,
                "year": engine.clock.year,
                "population": len(engine.agents),
                "tribes": len(engine.groups.active()),
            }
            if live:
                context["call"] = self.voice.snapshot(self._history())
                context["queued"] = self.voice.budget_busy()
            return context

    def _history(self) -> List[Dict[str, str]]:
        """Earlier exchanges as chat turns (the voice keeps only the last few)."""
        with self._lock:
            rows = [m for m in self._messages if m.role in ("player", "character") and not m.pending and m.text]
        return [{"role": "user" if m.role == "player" else "assistant", "content": m.text} for m in rows]

    def _send(self, raw: Any) -> Dict[str, Any]:
        text = str(raw or "").strip()[:MAX_TEXT]
        if not text:
            return {"ok": False, "error": "Mensagem vazia."}
        with self._lock:
            if self._busy:
                return {"ok": False, "error": f"{self.character} ainda está respondendo."}
            self._busy = True
        live = self._live()
        silent = None
        if self.engine.minds.paused:
            # The game's LLM switch is off: Arthur stays silent too.
            silent = "As chamadas de LLM estão desligadas (botão AI). Ligue para o rei responder."
        elif not self.llm_enabled:
            silent = "A conversa do Arthur está desligada na aba LLMs. Ligue para o rei responder."
        elif live:
            silent = self.voice.blocked() or None
        context = self._context(live and not silent)
        self._add("player", text, name="Você", day=context["day"])
        with self._lock:
            self.usage["messages"] += 1
        if silent:
            self._add("system", silent)
            with self._lock:
                self._busy = False
            return {"ok": True}
        if context.get("queued"):
            self._add("system", "O teto de chamadas por minuto está ocupado (tribos e conselho também usam). "
                                "Sua mensagem é a próxima da fila; pode levar até ~1 min.")
        pending = self._add("character", "", name=self.character, day=context["day"], pending=True)
        threading.Thread(
            target=self._answer, args=(pending.id, text, context),
            name="llworld-advisor", daemon=True,
        ).start()
        return {"ok": True}

    def _answer(self, message_id: int, text: str, context: Dict[str, Any]) -> None:
        failed, advice, note, out = False, None, "", {}
        try:
            role = "character"
            if "call" in context:
                out = self.voice.answer(text, context["call"])
                if out.get("blocked"):
                    role, body = "system", out["blocked"]  # no call was made
                else:
                    body, advice = out["text"], out["advice"]
                    if out["error"]:
                        # He says he needs time; the panel says why.
                        failed, note = True, f"A LLM falhou: {out['error']}"
            else:
                body = str(self._reply(text, context) or "").strip() or "…"
        except Exception as error:  # A failed reply must not wedge the panel.
            failed = True
            role, body = "system", f"{self.character} não conseguiu responder ({type(error).__name__})."
        with self._lock:
            self.usage["replies"] += 0 if failed or role != "character" else 1
            self.usage["failures"] += 1 if failed else 0
            if "call" in context and not out.get("blocked"):
                self.usage["llm_calls"] += 1
                self.usage["tokens_in"] += out.get("tokens_in", 0)
                self.usage["tokens_out"] += out.get("tokens_out", 0)
            for message in self._messages:
                if message.id == message_id:
                    message.role, message.text, message.pending = role, body, False
                    message.advice = advice
                    break
            self._busy = False
        if note:
            self._add("system", note)
