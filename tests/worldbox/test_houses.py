"""Optional houses (config.settlements.houses): off changes nothing; on spreads
homes over each settlement's domain. No network."""
import dataclasses, os, sys
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
    os.environ.pop(k, None)
from worldbox.ai import client
client._DOTENV_LOADED = True  # never read the real .env in tests
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine, SimulationRunner
from worldbox.cli.webview import LiveState

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

base = Config()
off = SimulationEngine(config=base, seed=42)
for _ in range(2500): off.step()
check("off by default: no houses", base.settlements.houses is False and all(not s.houses for s in off.settlements.active()))
check("off: /state has an empty house list", LiveState(off, SimulationRunner(off)).snapshot()["houseList"] == [])

cfg = dataclasses.replace(base, settlements=dataclasses.replace(base.settlements, houses=True))
eng = SimulationEngine(config=cfg, seed=42)
for _ in range(2500): eng.step()
towns = eng.settlements.active()
check("on: towns build houses", towns and all(s.houses for s in towns), [len(s.houses) for s in towns])
per, gap = cfg.settlements.people_per_house, cfg.settlements.house_spacing
ok_count, ok_reach, ok_walk = True, True, True
for s in towns:
    group = eng.groups.get(s.group_id)
    wanted = min(cfg.settlements.max_houses, -(-group.size // per))
    if len(s.houses) > wanted: ok_count = False
    reach = min(cfg.settlements.house_radius, 6 + 2 * int(s.level))
    for hx, hy in s.houses:
        if max(abs(hx - s.x), abs(hy - s.y)) > reach: ok_reach = False
        if not eng.world.is_passable(hx, hy): ok_walk = False
check("never more than one house per people_per_house", ok_count)
check("houses stay inside the domain", ok_reach)
check("houses on walkable land", ok_walk)
spots = [s.position for s in towns] + [h for s in towns for h in s.houses]
close = [(a, b) for i, a in enumerate(spots) for b in spots[i + 1:] if max(abs(a[0] - b[0]), abs(a[1] - b[1])) < gap]
check("houses keep their spacing", not close, close[:3])
member = next(a for a in eng.agents if eng.settlements.for_group(a.group_id) is not None)
town = eng.settlements.for_group(member.group_id)
home = eng._social_context(member, {}).home
check("a member's home is one of its town's houses", home in town.houses, (home, town.houses[:3]))
far = [h for h in town.houses if max(abs(h[0] - town.x), abs(h[1] - town.y)) > cfg.settlements.ration_radius]
check("/state lists every house", len(LiveState(eng, SimulationRunner(eng)).snapshot()["houseList"]) == 3 * sum(len(s.houses) for s in towns))
if far:
    hx, hy = far[0]
    member.x, member.y = hx, hy
    town.homes[member.id] = (hx, hy)
    town.food_store = 100.0
    check("a far house is a pantry", eng._draw_ration(member) > 0)

# Homes stay put while houses come and go.
before = {m: h for s in towns for m, h in s.homes.items()}
for _ in range(400): eng.step()
after = {m: h for s in eng.settlements.active() for m, h in s.homes.items()}
kept = [m for m in before if m in after]
moved = [m for m in kept if before[m] != after[m]]
standing = {h for s in eng.settlements.active() for h in s.houses}
check("homes are stable over a year", len(moved) <= len(kept) * 0.05, (len(moved), len(kept)))
check("every home is a standing house", all(h in standing for h in after.values()))

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
