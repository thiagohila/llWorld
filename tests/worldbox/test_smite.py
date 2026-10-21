"""Smite must kill everyone in range at once, without counting them as war dead."""
import collections, dataclasses, sys
sys.path.insert(0, sys.argv[1])
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine, SimulationRunner
from worldbox.cli.webview import LiveState

cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, enabled=False))
eng = SimulationEngine(config=cfg, seed=42); eng.run(1500)
state = LiveState(eng, SimulationRunner(eng))
spot = collections.Counter(a.position for a in eng.agents).most_common(1)[0][0]
ids = {a.id for a in eng.agents if max(abs(a.x - spot[0]), abs(a.y - spot[1])) <= 3}
deaths0, war0 = eng.total_deaths, eng.total_war_deaths
res = state.act("smite", spot[0], spot[1], 3)
alive = {a.id for a in eng.agents}
for _ in range(5): eng.step()
ok = (res["affected"] == len(ids) > 0 and not (ids & alive) and not (ids & {a.id for a in eng.agents})
      and eng.total_deaths - deaths0 >= len(ids) and eng.total_war_deaths == war0)
print(f"{'PASS' if ok else 'FAIL'} smite: {len(ids - alive)}/{len(ids)} dead at once, war deaths +{eng.total_war_deaths - war0}")
print("\nRESULT:", "all passed" if ok else "1 failed")
sys.exit(0 if ok else 1)
