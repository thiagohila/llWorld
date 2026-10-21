"""Benchmark: ms/day in two windows of one seeded run, and a fingerprint of final state."""
import sys, time, dataclasses, hashlib
sys.path.insert(0, sys.argv[1])
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine
cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, enabled=False))
eng = SimulationEngine(config=cfg, seed=42)
def window(n):
    t = time.perf_counter()
    for _ in range(n): eng.step()
    return (time.perf_counter() - t) * 1000 / n
a = window(3000); pa = len(eng.agents)
eng.run(5000)
b = window(1500); pb = len(eng.agents)
fp = hashlib.md5(repr([(x.id, x.x, x.y, round(x.needs.health, 6), x.goal, x.group_id) for x in eng.agents]).encode()).hexdigest()
print(f"days 0-3000: {a:.2f} ms/day (pop {pa}) | days 8000-9500: {b:.2f} ms/day (pop {pb}) | state {fp}")
