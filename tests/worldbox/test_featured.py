"""Featured people on the live map, and founding a tribe from outside. No network."""
import os, sys
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
    os.environ.pop(k, None)
from worldbox.ai import client
client._DOTENV_LOADED = True  # never read the real .env in tests
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine, SimulationRunner
from worldbox.cli.webview import LiveState
from worldbox.society.founding import found_tribe, settle_people

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

eng = SimulationEngine(config=Config(), seed=42)
state = LiveState(eng, SimulationRunner(eng))
check("nobody featured by default", state.snapshot()["featured"] == [])

x, y = eng.world.random_passable_tile(eng.rng)
before = len(eng.events.recent(100))
group, settlement, people = found_tribe(eng, x, y, 8, name="Test Realm", family="Testa", house="", houses=[""])
check("found_tribe plants the tribe", group in eng.groups.active() and group.name == "Test Realm" and len(people) == 8)
check("first person is chief", group.chieftain_id == people[0].id and people[0].family_name == "Testa")
check("with a camp", settlement is not None and eng.settlements.for_group(group.id) is settlement)
check("houses honoured", all(p.ai_house == "" for p in people))
check("records no event itself", len(eng.events.recent(100)) == before)
more = settle_people(eng, group, x, y, 3, "Testa", houses=[""])
check("settle_people joins the tribe", all(p.group_id == group.id for p in more) and group.size == 11)

hero = people[0]
state.feature(hero.id, "Hero of a very long name that will be trimmed down", "king")
f = state.snapshot()["featured"]
check("featured listed with position", len(f) == 1 and (f[0]["id"], f[0]["x"], f[0]["y"]) == (hero.id, hero.x, hero.y), f)
check("label trimmed, kind kept", len(f[0]["label"]) <= 40 and f[0]["kind"] == "king")
check("colour is the tribe's", f[0]["color"] == state._index_for(group.id))
hero.die("test", 0); eng.agents.remove(hero)
check("the dead drop off the list", state.snapshot()["featured"] == [])
state.feature(people[1].id, "B"); state.unfeature(people[1].id)
check("unfeature", state.snapshot()["featured"] == [])

r = state.found_civ(x, y, "Avalon", "", 10)
check("map's found button still works", r["ok"] and r["name"].startswith("Avalon"), r)

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
