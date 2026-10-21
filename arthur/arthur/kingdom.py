"""Arthur's kingdom in the world: founded at the start, ruled by him for good.

The game has no kings, so the rules that would end a reign are bent from
outside, without editing the game:

* **Fixed chieftain** -- the game picks a tribe's leader through
  ``culture.choose_chieftain`` (looked up on the module every day); the
  patched version returns the king whenever he is among the members.
* **Immortal** -- the king's health never drops below 1, he is immune to
  every disease and his age is pinned, so neither wounds, plague, hunger nor
  old age take him -- and no death or kill is ever counted for him. Smite
  from the map is aimed around him (``LiveState.act``).
* **One realm** -- ``GroupRegistry.try_split`` and ``find_unviable`` skip the
  kingdom, so it never splinters or disbands. If everyone but the king dies,
  a few settlers come to him.
* **Out of the LLM minds** -- the tribe follows the plain rules until
  Arthur's own mind arrives (stage 3), and does not take one of the slots.

The patches act only on objects marked with ``REALM``/``KING``, so a world
reset (new registry, ids starting over) cannot protect the wrong tribe.
Everything runs on the simulation thread or under ``runner.lock``.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from .bridge import DISEASES, EventKind, GroupRegistry, Needs, culture, found_tribe, settle_people
from .persona import ARTHUR

REALM = "llworld_realm"  # set on the kingdom's Group
KING = "llworld_king"  # set on the king's Agent
SETTLERS = 6  # who comes when the king is left alone
SITE_SAMPLES = 400


class KingNeeds(Needs):
    """A king's body: it suffers, but health never drops below 1.

    Clamping on every write (not only when death is checked) matters: a
    battle decides "fatal" from the raw health, and would otherwise credit
    someone with killing a king who did not die.
    """

    @property
    def health(self) -> float:
        return self._health

    @health.setter
    def health(self, value: float) -> None:
        self._health = max(1.0, float(value))

    def is_dead(self) -> bool:
        return False


def _is_realm(group: Any) -> bool:
    return bool(getattr(group, REALM, False))


def _is_king(agent: Any) -> bool:
    return bool(getattr(agent, KING, False))


_PATCHED = False


def install_rules() -> None:
    """Bend the game's succession, split and disband rules for marked realms (once)."""
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    choose = culture.choose_chieftain

    def choose_chieftain(members, days_per_year):
        for agent in members:
            if agent.alive and _is_king(agent):
                return agent
        return choose(members, days_per_year)

    culture.choose_chieftain = choose_chieftain

    try_split = GroupRegistry.try_split

    def no_split(self, group, members, day, rng):
        if _is_realm(group):
            return None
        return try_split(self, group, members, day, rng)

    GroupRegistry.try_split = no_split

    find_unviable = GroupRegistry.find_unviable

    def viable(self, day):
        return [group for group in find_unviable(self, day) if not _is_realm(group)]

    GroupRegistry.find_unviable = viable


class Kingdom:
    """Founds Arthur's kingdom in ``engine`` and keeps it, across world resets."""

    def __init__(self, engine: Any, runner: Any, live_state: Any = None, persona: Dict[str, Any] = ARTHUR) -> None:
        install_rules()
        self.engine = engine
        self.runner = runner
        self.live_state = live_state
        self.persona = persona
        self.king: Optional[Any] = None
        self.group: Optional[Any] = None
        self.age_days = 0
        self.crowned_day = 0
        self._hook_engine()
        self._hook_powers()
        self.found()

    # -- founding -------------------------------------------------------------

    def choose_site(self) -> Tuple[int, int]:
        """The most fertile walkable spot among a sample drawn from the seed.

        Uses its own generator, so the same seed always gives the same site
        whatever else has drawn from the engine's.
        """
        world = self.engine.world
        rng = random.Random(f"arthur-site-{self.engine.seed}")
        best, best_score = None, -1.0
        margin = 4
        for _ in range(SITE_SAMPLES):
            x, y = world.random_passable_tile(rng)
            if not (margin <= x < world.width - margin and margin <= y < world.height - margin):
                continue
            score = sum(
                world.resources.effective_capacity(tx, ty)
                for tx, ty in world.tiles_within(x, y, 3)
                if world.is_passable(tx, ty)
            )
            if score > best_score:
                best, best_score = (x, y), score
        return best or world.random_passable_tile(rng)

    def found(self) -> None:
        """Plant the kingdom with Arthur as its king."""
        persona = self.persona
        with self.runner.lock:
            engine = self.engine
            day = engine.clock.day
            dpy = engine.config.simulation.days_per_year
            x, y = self.choose_site()
            group, settlement, spawned = found_tribe(
                engine, x, y, persona["people"],
                name=persona["realm"], family=persona["family"], house="", houses=[""],
            )
            setattr(group, REALM, True)
            if settlement is not None:
                settlement.name = persona["seat"]

            king = spawned[0]
            setattr(king, KING, True)
            king.name = persona["name"]
            king.family_name = persona["family"]
            king.age_days = int(persona["age_years"] * dpy)
            king.lifespan_days = 10**9
            for trait, value in persona["traits"].items():
                setattr(king, trait, float(value))
            needs = king.needs
            king.needs = KingNeeds(hunger=needs.hunger, energy=needs.energy, health=needs.health)
            # Immune for good: a disease's lethality roll would otherwise count
            # a death that never happens, and leave him ill forever.
            for disease in DISEASES:
                king.immunities[disease.id] = None
            king.memory.note(day, f"was crowned king of the {group.name}")

            self.age_days = king.age_days
            self.crowned_day = day
            town = settlement.name if settlement else "open ground"
            engine.events.record(
                day, EventKind.SOCIETY,
                f"{king.full_name} was crowned king of the {group.name} at {town} "
                f"({len(spawned)} people)",
                agent_id=king.id,
            )
            if settlement is not None:
                engine.chronicle.note_settlement(
                    day, engine.clock.year, settlement.id, settlement.name,
                    int(settlement.level), settlement.level_name, group.name,
                )
            if self.live_state is not None:
                if self.king is not None and self.king is not king:
                    self.live_state.unfeature(self.king.id)
                self.live_state.feature(king.id, persona["name"], "king")
            self.king, self.group = king, group

    # -- keeping it -------------------------------------------------------------

    def upkeep(self) -> None:
        """Daily, after the game's own day: keep the king young and never alone."""
        king, group = self.king, self.group
        if king is None or group is None:
            return
        engine = self.engine
        king.age_days = self.age_days
        if king.group_id != group.id:  # Never expected; repaired rather than lost.
            king.group_id = group.id
        alive = sum(1 for agent in engine.agents if agent.group_id == group.id and agent.alive)
        if alive <= 1:
            settle_people(engine, group, king.x, king.y, SETTLERS, self.persona["family"], houses=[""])
            engine.events.record(
                engine.clock.day, EventKind.SOCIETY,
                f"{SETTLERS} settlers came to {king.name}'s side; the {group.name} lives on",
                agent_id=king.id,
            )

    def _hook_engine(self) -> None:
        engine = self.engine
        step, reset = engine.step, engine.reset
        minds = engine.minds

        def step_with_upkeep():
            report = step()
            self.upkeep()
            return report

        def reset_and_refound(seed=None):
            reset(seed)
            self.found()

        def eligible(eng):
            # Same rule as MindDirector._eligible, without the kingdom, so it
            # neither gets an LLM nor takes another tribe's slot.
            tribes = sorted(
                (group for group in eng.groups.active() if not _is_realm(group)),
                key=lambda group: -group.size,
            )
            return [
                group for group in tribes if group.size >= minds.config.min_tribe_size
            ][: minds.mind_slots()]

        engine.step = step_with_upkeep
        engine.reset = reset_and_refound
        minds._eligible = eligible

    def _hook_powers(self) -> None:
        """Smite from the map spares the king: he is set aside while it falls."""
        state = self.live_state
        if state is None:
            return
        act = state.act

        def act_sparing_the_king(tool, x, y, radius=3):
            if tool != "smite":
                return act(tool, x, y, radius)
            with self.runner.lock:
                engine = self.engine
                kings: List[Tuple[int, Any]] = [
                    (index, agent) for index, agent in enumerate(engine.agents) if _is_king(agent)
                ]
                if not kings:
                    return act(tool, x, y, radius)
                engine.agents = [agent for agent in engine.agents if not _is_king(agent)]
                try:
                    result = act(tool, x, y, radius)
                finally:
                    for index, agent in kings:
                        engine.agents.insert(min(index, len(engine.agents)), agent)
                result["spared"] = [agent.full_name for _, agent in kings
                                    if max(abs(agent.x - x), abs(agent.y - y)) <= radius]
                return result

        state.act = act_sparing_the_king

    # -- what Arthur's HUD shows ----------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """The king and his realm, for the HUD. Takes the lock."""
        with self.runner.lock:
            king, group = self.king, self.group
            if king is None or group is None:
                return {"ok": False}
            engine = self.engine
            dpy = engine.config.simulation.days_per_year
            settlement = engine.settlements.for_group(group.id)
            return {
                "ok": True,
                "id": king.id,
                "name": king.full_name,
                "title": self.persona["title"],
                "alive": king.alive,
                "chief": group.chieftain_id == king.id,
                "x": king.x,
                "y": king.y,
                "health": round(king.needs.health),
                "ill": king.infection is not None,
                "realm": group.name,
                "seat": settlement.name if settlement else "",
                "seatLevel": settlement.level_name if settlement else "",
                "people": group.size,
                "era": group.era,
                "years": round((engine.clock.day - self.crowned_day) / dpy, 1),
            }
