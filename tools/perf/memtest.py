"""Long run: Python heap and key collection sizes every 5000 days."""
import sys, time, tracemalloc, resource, dataclasses, gc
sys.path.insert(0, sys.argv[1])
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine
cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, enabled=False))
eng = SimulationEngine(config=cfg, seed=7); tracemalloc.start()
print("dia | pop | heap MB | pico MB | tribos | assent. | crônica | guerras hist | ms/dia")
for chunk in range(6):
    t = time.perf_counter(); n = 5000 if chunk else 1
    for _ in range(n): eng.step()
    ms = (time.perf_counter() - t) * 1000 / n; gc.collect()
    cur, peak = tracemalloc.get_traced_memory()
    print(f"{eng.clock.day:>6} | {len(eng.agents):>4} | {cur/1e6:7.1f} | {peak/1e6:7.1f} | {len(eng.groups.groups):>3} | {len(eng.settlements.settlements):>3} | {len(eng.chronicle):>4} | {len(eng.diplomacy.history):>3} | {ms:6.1f}", flush=True)
