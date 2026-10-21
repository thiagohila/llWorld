"""Arthur's kingdom (stage 2): founded on day zero, Arthur fixed and immortal,
one realm that never splits or disbands, out of the LLM slots, marked on the
map. Offline: no LLM, no network, no servers started.

Run from the llWorld root:  .venv/bin/python -I -B tests/arthur/test_kingdom.py "$PWD/arthur"
"""
import os, sys
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "LLM_MAX_MINDS"):
    os.environ.pop(k, None)
import run as arthur_run  # arthur/run.py
from worldbox.ai import client
client._DOTENV_LOADED = True  # never read the real .env in tests
from arthur.kingdom import KING, REALM, SETTLERS
from arthur.bridge import EventKind, settle_people

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

engine, runner, game, arthur = arthur_run.build(seed=42, no_ai=True, port=18765, arthur_port=18866)
kingdom = arthur.kingdom
king, realm = kingdom.king, kingdom.group
dpy = engine.config.simulation.days_per_year

def days(n):
    for _ in range(n):
        engine.step()

def death_events():
    return [e for e in engine.events.recent(10_000) if e.kind == EventKind.DEATH and e.agent_id == king.id]

# --- day zero ----------------------------------------------------------------
check("founded on day zero", engine.clock.day == 0 and realm in engine.groups.active())
check("Arthur Pendragon is the chief", king.full_name == "Arthur Pendragon" and realm.chieftain_id == king.id)
check("objects are marked", getattr(king, KING, False) and getattr(realm, REALM, False))
seat = engine.settlements.for_group(realm.id)
check("seat is Camelot", seat is not None and seat.name == "Camelot", seat and seat.name)
check("persona traits on the king", (king.aggression, king.caution, king.industry) == (0.35, 0.55, 0.6))
check("crowning recorded", any("crowned king" in e.message for e in engine.events.recent(50)))
snap = game.state.snapshot()
check("map marks the king", [f["id"] for f in snap["featured"]] == [king.id] and snap["featured"][0]["kind"] == "king")
again = arthur_run.build(seed=42, no_ai=True, port=18765, arthur_port=18866)[3].kingdom
check("same seed, same site", (again.king.x, again.king.y) == (king.x, king.y))

# --- a few years of plain play -------------------------------------------------
age = king.age_days
days(3 * dpy)
check("still alive, still chief after 3 years", king.alive and king in engine.agents and realm.chieftain_id == king.id)
check("age pinned", king.age_days == age, king.age_days)
check("realm still the same tribe", engine.groups.get(realm.id) is realm)
check("summary reads it", kingdom.summary()["chief"] and kingdom.summary()["years"] >= 3)

# --- what would kill anyone else -------------------------------------------------
king.needs.health = 0.0; king.needs.hunger = 100.0; king.needs.energy = 0.0
check("health never below 1", king.needs.health == 1.0)
days(5)
check("survives starvation and exhaustion", king.alive and king in engine.agents)
king.wounded_on_day = engine.clock.day; king.needs.health = -40
days(1)
check("survives battle wounds", king.alive)
check("immune to every disease", all(not king.is_susceptible_to(d, engine.clock.day) for d in ("fever", "flux", "pox", "plague", "coughing")))
r = game.state.act("smite", king.x, king.y, 2)
check("smite spares the king", king.alive and engine.agents.count(king) == 1 and r.get("spared") == ["Arthur Pendragon"], r)
check("no death ever recorded for him", death_events() == [])

# --- alone, the realm gets settlers ---------------------------------------------
for agent in engine.agents:
    if agent.group_id == realm.id and agent is not king:
        agent.die("test", engine.clock.day)
engine.agents = [a for a in engine.agents if a.alive]
days(1)
members = [a for a in engine.agents if a.group_id == realm.id]
check("settlers come when he is alone", len(members) == 1 + SETTLERS, len(members))
check("unviable rule skips the realm", realm not in engine.groups.find_unviable(engine.clock.day + 10**6))

# --- too big to hold together, for anyone else ------------------------------------
split = engine.config.groups.split_size
settle_people(engine, realm, king.x, king.y, split + 10, "Pendragon", houses=[""])
days(3)
check("never splits", engine.groups.get(realm.id) is realm and realm.size >= split
      and not any("Kingdom of Arthur splintered" in e.message for e in engine.events.recent(500)), realm.size)

# --- out of the LLM slots -------------------------------------------------------
minds = engine.minds
eligible = minds._eligible(engine)
others = sorted((g for g in engine.groups.active() if g is not realm and g.size >= minds.config.min_tribe_size), key=lambda g: -g.size)
check("realm never gets an LLM slot", realm not in eligible)
check("slots go to the other tribes", eligible == others[: minds.mind_slots()], ([g.id for g in eligible], [g.id for g in others[:3]]))
check("king is in no tribe's member list but his", sum(king.id in g.member_ids for g in engine.groups.active()) == 1)

# --- the chief rule leaves other tribes alone -------------------------------------
other = next((g for g in engine.groups.active() if g is not realm and g.size > 0), None)
if other is not None:
    chief = engine.get_agent(other.chieftain_id)
    check("other tribes still pick their own chiefs", chief is not None and not getattr(chief, KING, False))

# --- world reset ----------------------------------------------------------------
old_king, old_realm = king, realm
engine.reset(7)
king, realm = kingdom.king, kingdom.group
check("reset refounds the kingdom", realm is not old_realm and realm in engine.groups.active() and getattr(realm, REALM, False))
check("new king chief of the new realm", realm.chieftain_id == king.id and king.full_name == "Arthur Pendragon")
check("only the new realm is protected", [g.id for g in engine.groups.active() if getattr(g, REALM, False)] == [realm.id])
check("map marks only the new king", [f["id"] for f in game.state.snapshot()["featured"]] == [king.id])
days(400)
check("still chief after reset and a year", king.alive and realm.chieftain_id == king.id)

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
