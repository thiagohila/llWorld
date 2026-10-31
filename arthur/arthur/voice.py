"""Arthur's voice: the king answers his advisor (stage 4a).

The advisor (``advisor.Advisor``) owns the conversation; this answers each
message. Arthur reads his persona, the same report his council reads (his
realm, neighbours, wars, granary), his own recent decisions with their
reasons, and the last few exchanges -- nothing else, so he cannot know what
the report does not say. He replies in character, in Portuguese, and says
what he makes of any advice: accept, consider, reject or ask to clarify.

Talking never changes the world. Advice he accepts or will consider is
handed to his council (``Council.hear``), which weighs it at his next
decision (stage 4b); advice he turns down is not.

Cost: the same master switch, per-minute budget and quota gate as his council.
The tribes and the council usually keep the per-minute budget busy, so a
message waits for a free slot (up to ``BUDGET_WAIT`` seconds) instead of
being turned away -- and while it waits, everyone else sees one slot less
(``minds.call_cap`` is wrapped), so the player's message goes first.
Without an LLM (``--no-ai``, no source) the advisor keeps its offline stand-in.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from .bridge import brief_tribe, chat, extract_json
from .quota import QuotaGate

HISTORY_EXCHANGES = 6
BUDGET_WAIT = 75.0  # a slot frees when the oldest call leaves the 60 s window: always within this
MAX_TOKENS = 500
MAX_REPLY = 1200
VERDICTS = ("accept", "consider", "reject", "clarify")
FALLBACK = "Preciso pensar nisso. Fale comigo de novo daqui a pouco."

SYSTEM_PROMPT = """\
You are {title} {name} {family}, ruler of the {realm}, seat at {seat}, in a \
civilisation simulator. The player is your advisor and speaks to you in \
Portuguese.

Who you are: {temperament}. You {voice}.
Your goals, most important first:
{goals}
Your red lines (never cross them):
{red_lines}

What you know is the report below and nothing else. If you are asked about \
something it does not say, you do not know it: say so, in character. Never \
invent events, numbers, places or people. The report calls your kingdom a \
"tribe"; to you it is your kingdom, and other tribes are peoples or \
neighbours.

You decide alone. Talking does not change the world: your decisions are \
made at your council, every 40 days or so (sooner when something urgent \
happens). Never say you have already ordered or done something because of \
this conversation; at most, that you will weigh it at your next council.

When the advisor gives advice (asks you to do, change or avoid something), \
judge it against your goals, your red lines and the report, and say what \
you make of it. Advice that crosses a red line is always rejected.

Reply with one JSON object and nothing else:
{{"reply": <your words to the advisor, in Portuguese (Brazil), in character, \
one to four sentences>, "advice": <null if there was no advice, else \
{{"summary": <the advice in a few words, Portuguese>, "verdict": \
"accept" | "consider" | "reject" | "clarify", "urgent": <true only if it \
cannot wait for your usual council>}}>}}

Report (day {day}, year {year}):
{report}
"""


def _report(engine: Any, kingdom: Any) -> str:
    """The council's report, minus the lines that only make sense for a decision."""
    lines = [
        line.replace("You are the mind of the ", "Your kingdom: the ", 1)
        for line in brief_tribe(engine, kingdom.group).splitlines()
        if not line.startswith("You may set")
    ]
    council = kingdom.council
    if council.log:
        lines.append("Your recent decisions at the council (newest first):")
        for entry in list(council.log)[:3]:
            lines.append(f"  day {entry['day']}: {entry['stance']} -- {entry['intent']} "
                         f"(your reason: {entry['rationale']})")
    else:
        lines.append("You have not held your council yet.")
    return "\n".join(lines)


def parse_reply(text: str) -> Dict[str, Any]:
    """The king's words and his reading of the advice; raises ValueError if unusable."""
    try:
        raw = extract_json(text)
    except (ValueError, json.JSONDecodeError):
        raw = None
    if not isinstance(raw, dict):
        # A model that ignored the format still said something: keep the words.
        words = (text or "").strip()
        if not words or words.startswith("{"):
            raise ValueError("no reply")
        return {"text": words[:MAX_REPLY], "advice": None}
    words = str(raw.get("reply") or "").strip()
    if not words:
        raise ValueError("empty reply")
    advice = raw.get("advice")
    reading: Optional[Dict[str, Any]] = None
    if isinstance(advice, dict) and advice.get("verdict") in VERDICTS:
        summary = str(advice.get("summary") or "").strip().replace("\n", " ")[:160]
        if summary:
            reading = {
                "summary": summary,
                "verdict": advice["verdict"],
                "urgent": advice.get("urgent") is True and advice["verdict"] in ("accept", "consider"),
            }
    return {"text": words[:MAX_REPLY], "advice": reading}


class KingVoice:
    """What answers the advisor's messages, through the council's LLM source."""

    uses_llm = True

    def __init__(self, kingdom: Any, quota: Optional[QuotaGate] = None) -> None:
        self.kingdom = kingdom
        self.engine = kingdom.engine
        self.quota = quota or kingdom.council.quota
        self.budget_wait = BUDGET_WAIT
        self._waiting = 0
        minds = self.engine.minds
        self._cap = minds.call_cap

        def call_cap() -> int:
            cap = self._cap()
            return max(0, cap - 1) if self._waiting else cap

        minds.call_cap = call_cap

    @property
    def model(self) -> str:
        house = self.kingdom.council.house()
        return house.get("label", "—") if house else "—"

    def live(self) -> bool:
        """An LLM can answer at all (else the advisor uses its stand-in)."""
        return bool(self.engine.config.ai.enabled) and bool(self.kingdom.council.house())

    def blocked(self) -> str:
        """Why the king cannot be asked right now ("" if he can). Takes no lock."""
        minds = self.engine.minds
        if minds.halted:
            return f"As chamadas de LLM pararam: {minds.halted[:120]}"
        if not self.quota.open():
            minutes = max(1, -(-self.quota.retry_in() // 60))
            return (f"A cota da LLM está esgotada (429). O rei volta a responder em ~{minutes} min; "
                    "a espera aumenta se o provedor seguir recusando.")
        if self._cap() <= 0:
            return "O teto de chamadas por minuto está em zero (aba LLMs)."
        return ""

    def budget_busy(self) -> bool:
        """The per-minute budget is full right now (the message will wait). Call under runner.lock."""
        minds = self.engine.minds
        return self._cap() - minds.calls_last_minute() <= 0

    def snapshot(self, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Everything the call needs, read under ``runner.lock`` by the advisor."""
        p, engine = self.kingdom.persona, self.engine
        seat = engine.settlements.for_group(self.kingdom.group.id) if self.kingdom.group else None
        system = SYSTEM_PROMPT.format(
            title=p["title"], name=p["name"], family=p["family"], realm=p["realm"],
            seat=seat.name if seat is not None else p["seat"],
            temperament=", ".join(p["temperament"]), voice=p["voice"],
            goals="\n".join(f"{i}. {g}" for i, g in enumerate(p["goals"], 1)),
            red_lines="\n".join(f"- {r}" for r in p["red_lines"]),
            day=engine.clock.day, year=engine.clock.year, report=_report(engine, self.kingdom),
        )
        return {
            "messages": [{"role": "system", "content": system}] + history[-2 * HISTORY_EXCHANGES:],
            "house": self.kingdom.council.house()["house"],
            "generation": self.kingdom.council.generation,
            "day": engine.clock.day,
            "timeout": engine.minds.config.timeout_seconds,
        }

    def _claim(self) -> bool:
        """Take one call from the shared per-minute budget, waiting for room."""
        minds = self.engine.minds
        deadline = time.monotonic() + self.budget_wait
        self._waiting += 1  # the others see one slot less meanwhile
        try:
            while True:
                with self.kingdom.runner.lock:
                    if self._cap() - minds.calls_last_minute() > 0:
                        minds._recent_calls.append(time.monotonic())  # Same window as the tribe minds.
                        return True
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.1)
        finally:
            self._waiting -= 1

    def answer(self, text: str, call: Dict[str, Any]) -> Dict[str, Any]:
        """Ask the model (worker thread, no lock held)."""
        if not self._claim():
            return {"blocked": "O teto de chamadas por minuto ficou cheio por mais de 1 min (as tribos e o conselho "
                               "também usam). Tente de novo, ou aumente o teto na aba LLMs."}
        messages = call["messages"] + [{"role": "user", "content": text}]
        result = chat(messages=messages, model=call["house"], timeout=call["timeout"], retries=1,
                      backoff=1.0, temperature=0.8, max_tokens=MAX_TOKENS, json_mode=True)
        self.quota.record(result)
        out: Dict[str, Any] = {"tokens_in": result.tokens_in, "tokens_out": result.tokens_out,
                               "text": FALLBACK, "advice": None, "error": ""}
        if not result.ok:
            if result.fatal:
                self.engine.minds.halted = result.error  # Same key as the tribe minds.
            out["error"] = (result.error or "call failed")[:160]
            return out
        try:
            out.update(parse_reply(result.text))
        except ValueError as error:
            out["error"] = f"resposta inutilizável ({error})"
            return out
        advice = out["advice"]
        if advice is not None and advice["verdict"] in ("accept", "consider"):
            with self.kingdom.runner.lock:
                council = self.kingdom.council
                if council.generation == call["generation"]:  # not about a world since reset
                    council.hear(advice, text, call["day"])
        return out
