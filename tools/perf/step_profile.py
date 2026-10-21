"""Per-day step cost vs population, plus where time goes at the end."""
import sys, time, cProfile, pstats, io, dataclasses
sys.path.insert(0, sys.argv[1])
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine

days = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
cfg = Config()
cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, enabled=False))
eng = SimulationEngine(config=cfg, seed=42)
buckets = {}
samples = []
t_all = time.perf_counter()
for d in range(days):
    t = time.perf_counter(); eng.step(); dt = (time.perf_counter() - t) * 1000
    pop = len(eng.agents)
    b = (pop // 100) * 100
    buckets.setdefault(b, []).append(dt)
    if d % 2000 == 0:
        samples.append((d, pop, len(eng.groups.active()), dt))
    if not eng.agents:
        break
total = time.perf_counter() - t_all
print(f"simulated {d+1} days in {total:.1f}s -> {(d+1)/total:.0f} days/s average")
print("\npop bucket | days | mean ms/day | p95 ms | max ms")
for b in sorted(buckets):
    v = sorted(buckets[b]); n = len(v)
    print(f"{b:>5}-{b+99:<5}| {n:>5} | {sum(v)/n:>8.2f} | {v[int(n*.95)-1 if n>1 else 0]:>6.2f} | {v[-1]:>6.1f}")
print("\nday | pop | tribes | ms that day")
for s in samples: print(*s)
# profile 300 days at the final population
pr = cProfile.Profile(); pr.enable()
for _ in range(300): eng.step()
pr.disable()
s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(28)
print(f"\n=== profile of 300 days at pop {len(eng.agents)} ===")
print("\n".join(l for l in s.getvalue().splitlines() if l.strip())[:6000])
