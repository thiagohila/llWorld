"""Does a day get dearer as the world ages, independent of population? Seed 7, no tracemalloc."""
import sys, time, dataclasses, cProfile, pstats, io
sys.path.insert(0, sys.argv[1])
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine
cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, enabled=False))
eng = SimulationEngine(config=cfg, seed=7)
print("janela | pop média | ms/dia | ms por 100 pessoas", flush=True)
for w in range(5):
    t = time.perf_counter(); pops = []
    for _ in range(5000): eng.step(); pops.append(len(eng.agents))
    ms = (time.perf_counter() - t) * 1000 / 5000; p = sum(pops) / len(pops)
    print(f"{w*5}k-{(w+1)*5}k | {p:6.0f} | {ms:6.2f} | {ms/p*100:5.2f}", flush=True)
pr = cProfile.Profile(); pr.enable()
for _ in range(300): eng.step()
pr.disable(); s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(16)
print("pop", len(eng.agents)); print("\n".join(l for l in s.getvalue().splitlines() if l.strip())[-2600:])
