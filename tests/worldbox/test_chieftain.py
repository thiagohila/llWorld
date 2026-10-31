"""Optional stable chieftain (config.culture.stable_chieftain): off, a leader
can lose the post while alive; on, they keep it until they die or leave. No LLM.

Run from the llWorld root:  .venv/bin/python -I -B tests/worldbox/test_chieftain.py "$PWD/worldbox"
"""
import dataclasses, os, sys
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
    os.environ.pop(k, None)
from worldbox.ai import client
client._DOTENV_LOADED = True  # never read the real .env in tests
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

def watch(stable, days=2000):
    """Leader changes: (deposed while alive and still in the tribe, successions, tribes-days with no chief)."""
    base = Config()
    cfg = dataclasses.replace(base, ai=dataclasses.replace(base.ai, enabled=False),
                              culture=dataclasses.replace(base.culture, stable_chieftain=stable))
    eng = SimulationEngine(config=cfg, seed=42)
    chiefs, deposed, successions, leaderless = {}, 0, 0, 0
    for _ in range(days):
        eng.step()
        people = {a.id: a for a in eng.agents}
        for group in eng.groups.active():
            before, now = chiefs.get(group.id), group.chieftain_id
            if now is None:
                leaderless += 1
            elif before is not None and before != now:
                old = people.get(before)
                if old is not None and old.alive and old.group_id == group.id:
                    deposed += 1
                else:
                    successions += 1
            chiefs[group.id] = now
    return eng, (deposed, successions, leaderless)

check("off by default", Config().culture.stable_chieftain is False)
_, off = watch(False)
check("off: leaders lose the post while alive (the old behaviour)", off[0] > 0, off)
eng, on = watch(True)
check("on: nobody is deposed while alive and in the tribe", on[0] == 0, on)
check("on: tribes still always have a chief", on[2] == 0, on)
group = max(eng.groups.active(), key=lambda g: g.size)
chief = next(a for a in eng.agents if a.id == group.chieftain_id)
chief.alive = False  # the chief dies
eng.step()
heir = next((a for a in eng.agents if a.id == group.chieftain_id), None)
check("on: when the chief dies, a living member takes over", heir is not None and heir.id != chief.id
      and heir.alive and heir.group_id == group.id, (chief.id, group.chieftain_id))

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
