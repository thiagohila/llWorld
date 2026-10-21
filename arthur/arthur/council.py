"""Arthur's council: the king decides his kingdom's policy (stage 3).

Every other tribe is played by the game's own minds. Arthur's realm is not:
it takes no LLM slot, and its policy comes from here -- his persona plus the
same situation report a tribe mind reads, answered with a policy in the
game's own format and a rationale. The game validates it (``parse_policy``)
and Arthur adds his own checks: no unknown tribes, no inventions the land
cannot support, and his red line (no war on a people at peace with us).

The engine reads the policy through ``engine.minds.policy_for`` (wrapped by
the kingdom), so it acts on roles, behaviour and research like any tribe's.
Diplomacy is the one effect the game applies from its own policy table, so
the council pushes relations itself, by the same daily amounts.

Cost: the council obeys the game's master switch (``minds.paused``) and its
own, takes its calls from the same per-minute budget as the tribe minds
(``call_cap`` / ``calls_last_minute``), and thinks on the minds' cadence
(``think_interval_days``, ``min_think_seconds``), skipping when nothing
changed -- except that a war starting or ending, the granary running low or
having no policy at all make him think at the next chance.

Calls run on a worker thread; results land in a queue drained on the
simulation thread. Each world gets a new generation, so an answer about a
world that was reset is dropped.
"""

from __future__ import annotations

import json
import queue
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Deque, Dict, List, Optional, Tuple

from .bridge import (
    ChatResult, EventKind, available_houses, brief_tribe, chat, extract_json, house_spec,
    parse_policy, scan_materials, situation_signature, validate_proposal,
)

LOW_GRANARY = 0.25  # below this fraction full, the king is asked to think now...
REARM_GRANARY = 0.40  # ...and not again until it has been back above this
MIN_TRIGGER_DAYS = 10  # an early thought waits at least this long after the last
MAX_TOKENS = 700
LOG_SIZE = 30
DIPLOMACY_DELTAS = {"war": -3.2, "peace": 2.4, "trade": 1.6, "ignore": 0.0}  # as the game's minds

SYSTEM_PROMPT = """\
You are {title} {name} {family}, ruler of the {realm}, seat at {seat}, in a \
civilisation simulator. Each time you are asked, you decide what your people \
do next. Your choice changes the world: who farms, who fights, how far your \
people roam, how you treat each neighbour, and what you try to invent.

Who you are: {temperament}. You {voice}.
Your goals, most important first:
{goals}
Your red lines (never cross them):
{red_lines}

The report below calls your kingdom a "tribe" and you its "mind"; that is \
the simulator's wording. Use only tribe_id values, places and materials it \
gives you.

Reply with one JSON object and nothing else:
{{"policy": {{"stance":"farm","warrior_share":0.12,"farmer_share":0.40,\
"scholar_share":0.10,"healer_share":0.08,"cohesion":0.7,"fight":0.8,\
"flee":1.1,"seek_food":1.2,"seek_mate":1.0,\
"toward":[{{"tribe_id":2,"action":"trade"}}],"invent":null,\
"intent":"Fill the granaries before winter."}},
 "rationale":"Uma ou duas frases, em português, explicando a decisão."}}

Rules for policy:
- stance is one of: survive, farm, expand, defend, research, raid, trade
- shares are 0..1 fractions of working adults; leftover people forage
- fight/flee/seek_food/seek_mate multiply how strongly people pick that action
- cohesion 0 = scatter and claim ground, 1 = huddle at home
- toward.action is war, peace, trade, or ignore
- invent is one new craft or null: {{"name":..., "from":[materials], \
"effect": food|combat|research|health|fertility|medicine, "why":...}}, using \
only materials listed in the report
- intent: one short sentence in English, as a king would say it
rationale: in Portuguese (Brazil), one or two sentences, why you chose this.
"""


def _red_line_forbids_war(engine: Any, realm: Any, other_id: int) -> bool:
    """War on a people at peace with us, unprovoked: not at war, relation not hostile."""
    diplomacy = engine.diplomacy
    return not diplomacy.at_war(realm.id, other_id) and diplomacy.relation(realm.id, other_id) >= 0.0


class Council:
    """Thinks for Arthur's realm and holds the policy the engine follows."""

    def __init__(self, engine: Any, runner: Any, persona: Dict[str, Any]) -> None:
        self.engine = engine
        self.runner = runner
        self.persona = persona
        self.enabled = True  # Arthur's own switch, under the game's master switch.
        self.log: Deque[Dict[str, Any]] = deque(maxlen=LOG_SIZE)
        self._inbox: "queue.Queue[Tuple[int, int, str, Any]]" = queue.Queue()
        self._pool: Optional[ThreadPoolExecutor] = None
        self.usage: Dict[str, int] = {"calls": 0, "skipped": 0, "failures": 0,
                                      "tokens_in": 0, "tokens_out": 0, "tokens_cached": 0}
        self.generation = 0
        self.reset(None)

    # -- lifecycle -------------------------------------------------------------

    def reset(self, realm: Optional[Any]) -> None:
        """A new world (or a new realm): forget the policy, drop answers in flight."""
        self.generation += 1
        self.realm = realm
        self.policy: Optional[Any] = None
        self.rationale = ""
        self.error = ""
        self.pending = False
        self.reason = ""
        self.last_day: Optional[int] = None
        self.last_wall = 0.0
        self.failures = 0
        self.retry_day = -1
        self.retry_wall = 0.0
        self.signature: Optional[Tuple[Any, ...]] = None
        self.skips = 0
        self.wars: Tuple[int, ...] = ()
        self.granary_low = False
        self.log.clear()

    def forget(self) -> bool:
        """Drop the current policy (the game's "forget decisions"); he thinks again soon."""
        had = self.policy is not None
        self.policy = None
        self.rationale = ""
        self.signature = None
        return had

    # -- what the engine and the HUD read ------------------------------------------

    def house(self) -> Dict[str, Any]:
        """The LLM source Arthur speaks through: the .env's own endpoint if set
        (v1: Gemini), else the first usable one."""
        usable = available_houses()
        return next((s for s in usable if s["house"] == "custom"), usable[0] if usable else {})

    def status(self) -> str:
        minds = self.engine.minds
        if not self.engine.config.ai.enabled:
            return "off_no_ai"
        if not self.house():
            return "no_source"
        if minds.halted:
            return "halted"
        if minds.paused:
            return "off_master"
        if not self.enabled:
            return "off_own"
        if self.pending:
            return "thinking"
        if self.error:
            return "error"
        return "on"

    def summary(self) -> Dict[str, Any]:
        policy = self.policy
        return {
            "status": self.status(),
            "model": self.house().get("label", "—") if self.house() else "—",
            "error": self.error,
            "policy": None if policy is None else {
                "stance": policy.stance, "intent": policy.intent, "day": policy.thought_day,
                "toward": [{"id": tid, "action": action} for tid, action in policy.toward],
                "invent": policy.invent.name if policy.invent is not None else "",
                "shares": {"warrior": policy.warrior_share, "farmer": policy.farmer_share,
                           "scholar": policy.scholar_share, "healer": policy.healer_share},
            },
            "rationale": self.rationale,
            "log": list(self.log),
        }

    def usage_snapshot(self) -> Dict[str, Any]:
        return dict(self.usage)

    # -- the daily turn (simulation thread, under runner.lock) ---------------------------

    def tick(self, day: int) -> None:
        engine = self.engine
        if not engine.config.ai.enabled or self.realm is None:
            return
        self._drain(day)
        minds = engine.minds
        if not minds.available():
            return
        self._nudge_diplomacy()
        if minds.paused or not self.enabled or self.pending:
            return
        self._maybe_think(day)

    def _situation(self) -> Tuple[str, Tuple[int, ...], bool]:
        """A reason to think before the usual interval ("" if none), plus the
        war list and granary state it was judged from. Nothing is remembered
        here: the state is only taken as seen once he actually thinks, so a
        trigger that has to wait (budget, pacing) is not lost."""
        engine, realm = self.engine, self.realm
        wars = tuple(sorted(
            other for key, war in engine.diplomacy.wars.items()
            if war.active and realm.id in key for other in key if other != realm.id
        ))
        settlement = engine.settlements.for_group(realm.id)
        fraction = settlement.store_fraction() if settlement is not None else 1.0
        if fraction < LOW_GRANARY:
            low = True
        elif fraction > REARM_GRANARY:
            low = False
        else:
            low = self.granary_low  # in between: keep the state, no new alarm
        reason = ""
        if self.policy is None:
            reason = "no policy"
        elif wars != self.wars:
            reason = "war changed"
        elif fraction < LOW_GRANARY and not self.granary_low:
            reason = "granary low"
        return reason, wars, low

    def _maybe_think(self, day: int) -> None:
        engine, realm, minds = self.engine, self.realm, self.engine.minds
        config = minds.config
        now = time.monotonic()
        if day < self.retry_day or now < self.retry_wall:
            return
        reason, wars, low = self._situation()
        if self.last_day is not None:
            if now - self.last_wall < config.min_think_seconds:
                return
            if reason and self.policy is not None and day - self.last_day < MIN_TRIGGER_DAYS:
                return
            if not reason:
                if day - self.last_day < config.think_interval_days:
                    return
                signature = situation_signature(engine, realm)
                if config.skip_unchanged and signature == self.signature and self.skips < config.max_unchanged_skips:
                    self.skips += 1
                    self.last_day, self.last_wall = day, now
                    self.granary_low = low
                    self.usage["skipped"] += 1
                    return
        if minds.call_cap() - minds.calls_last_minute() <= 0:
            return  # The shared budget is spent; try again on a later day.
        house = self.house()
        if not house:
            return
        self.wars, self.granary_low = wars, low
        self._ask(day, house, now, reason or "interval")

    def _messages(self) -> List[Dict[str, str]]:
        p = self.persona
        system = SYSTEM_PROMPT.format(
            title=p["title"], name=p["name"], family=p["family"], realm=p["realm"], seat=p["seat"],
            temperament=", ".join(p["temperament"]), voice=p["voice"],
            goals="\n".join(f"{i}. {g}" for i, g in enumerate(p["goals"], 1)),
            red_lines="\n".join(f"- {r}" for r in p["red_lines"]),
        )
        report = brief_tribe(self.engine, self.realm)
        if self.policy is not None:
            # The game's report reads the last intent from its own table, where
            # Arthur's policy does not live.
            report += f"\nYour last decision (day {self.policy.thought_day}): {self.policy.stance} -- {self.policy.intent}"
        return [{"role": "system", "content": system}, {"role": "user", "content": report}]

    def _ask(self, day: int, house: Dict[str, Any], now: float, reason: str) -> None:
        minds = self.engine.minds
        messages = self._messages()
        self.signature = situation_signature(self.engine, self.realm)
        self.skips = 0
        self.pending = True
        self.last_day, self.last_wall = day, now
        minds._recent_calls.append(now)  # Same per-minute window as the tribe minds.
        self.usage["calls"] += 1
        self.reason = reason
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="arthur-council")
        generation, timeout = self.generation, minds.config.timeout_seconds

        def think() -> ChatResult:
            return chat(messages=messages, model=house["house"], timeout=timeout, retries=1,
                        backoff=1.0, temperature=0.6, max_tokens=MAX_TOKENS, json_mode=True)

        def done(future) -> None:
            try:
                result = future.result()
            except Exception as error:  # A worker fault must not kill the pool.
                result = ChatResult(error=str(error))
            self._inbox.put((generation, day, house.get("label", house["house"]), result))

        self._pool.submit(think).add_done_callback(done)

    def _drain(self, day: int) -> None:
        while True:
            try:
                generation, thought_day, label, result = self._inbox.get_nowait()
            except queue.Empty:
                return
            if generation != self.generation:
                continue  # An answer about a world that no longer exists.
            self.pending = False
            self.usage["tokens_in"] += result.tokens_in
            self.usage["tokens_out"] += result.tokens_out
            self.usage["tokens_cached"] += result.tokens_cached
            if not result.ok:
                if result.fatal:
                    # Same key as the tribe minds: they would fail the same way.
                    self.engine.minds.halted = result.error
                self._fail(day, result.error or "call failed")
                continue
            try:
                policy, rationale, vetoes = self._validate(result.text, thought_day, label)
            except (ValueError, json.JSONDecodeError) as error:
                self._fail(day, f"Could not use the decision: {error}")
                continue
            self._apply(day, policy, rationale, vetoes)

    def _fail(self, day: int, error: str) -> None:
        """Keep the previous policy; wait longer after each failure (like the minds)."""
        config = self.engine.minds.config
        self.error = error[:200]
        self.failures += 1
        self.usage["failures"] += 1
        factor = min(config.failure_backoff_cap, 2 ** (self.failures - 1))
        self.retry_day = day + config.think_interval_days * factor
        self.retry_wall = time.monotonic() + config.failure_backoff_seconds * factor

    def _validate(self, text: str, day: int, label: str) -> Tuple[Any, str, List[str]]:
        """The game's checks (parse_policy) plus Arthur's own."""
        engine, realm = self.engine, self.realm
        raw = extract_json(text)
        body = raw.get("policy") if isinstance(raw.get("policy"), dict) else raw
        if not body or not any(k in body for k in ("stance", "toward", "intent", "farmer_share")):
            raise ValueError("empty decision")
        policy = parse_policy(body, day, f"Arthur · {label}", era=realm.era)
        rationale = str(raw.get("rationale") or "").strip().replace("\n", " ")[:300]

        vetoes: List[str] = []
        kept = []
        for other_id, action in policy.toward:
            other = engine.groups.get(other_id)
            if other is None or other_id == realm.id:
                vetoes.append(f"tribe {other_id} unknown")
                continue
            if action == "war" and _red_line_forbids_war(engine, realm, other_id):
                vetoes.append(f"no unprovoked war on {other.name}")
                continue
            kept.append((other_id, action))
        policy.toward = kept
        if policy.stance == "raid" and not any(a == "war" for _, a in kept):
            # With no target, a raid leans on the worst neighbour: same red line.
            worst = engine.diplomacy.relation_summary(realm.id, engine.groups)
            if not worst or _red_line_forbids_war(engine, realm, worst[0][0].id):
                vetoes.append("raid with no enemy became defend")
                policy.stance = "defend"
        if policy.invent is not None:
            problem = validate_proposal(policy.invent, realm, scan_materials(engine, realm), engine.config.ai)
            if problem:
                vetoes.append(f"invention dropped: {problem}")
                policy.invent = None
        if not rationale:
            rationale = policy.intent or policy.stance
        return policy, rationale, vetoes

    def _apply(self, day: int, policy: Any, rationale: str, vetoes: List[str]) -> None:
        engine, realm = self.engine, self.realm
        previous = self.policy
        self.policy, self.rationale = policy, rationale
        self.error = ""
        self.failures, self.retry_day, self.retry_wall = 0, -1, 0.0
        self.log.appendleft({
            "day": day, "year": engine.clock.year, "stance": policy.stance, "intent": policy.intent,
            "rationale": rationale, "model": policy.model, "vetoes": vetoes, "reason": self.reason,
            "toward": [{"id": tid, "action": action} for tid, action in policy.toward],
        })
        if previous is None or previous.stance != policy.stance or previous.intent != policy.intent:
            engine.events.record(
                day, EventKind.MIND,
                f"{self.persona['title']} {self.persona['name']} chose to {policy.stance}: "
                f"{policy.intent or policy.stance}",
            )
        if policy.invent is not None and (previous is None or previous.invent is None
                                          or previous.invent.tech_id != policy.invent.tech_id):
            engine.events.record(day, EventKind.MIND, f"The {realm.name} began work on {policy.invent.name}")

    def _nudge_diplomacy(self) -> None:
        """Push relations by the policy's toward-list, as the game does for its minds."""
        engine, realm, policy = self.engine, self.realm, self.policy
        if policy is None or not engine.config.diplomacy.enabled:
            return
        targets = list(policy.toward)
        if not targets and policy.stance in ("raid", "trade"):
            neighbours = engine.diplomacy.relation_summary(realm.id, engine.groups)
            if neighbours:
                target = neighbours[0][0].id
                if policy.stance == "trade" or not _red_line_forbids_war(engine, realm, target):
                    targets = [(target, "war" if policy.stance == "raid" else "trade")]
        for other_id, action in targets:
            if other_id == realm.id or engine.groups.get(other_id) is None:
                continue
            delta = DIPLOMACY_DELTAS.get(action, 0.0)
            if delta:
                engine.diplomacy.adjust(realm.id, other_id, delta)
