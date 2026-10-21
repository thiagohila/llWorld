"""Runtime LLM controls: switch calls off/on, rate cap, forget policies. No network."""
import dataclasses, json, os, sys, time
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "LLM_MAX_CALLS_PER_MINUTE"):
    os.environ.pop(k, None)
os.environ["DEEPSEEK_API_KEY"] = "dummy-not-a-key"
from worldbox.ai import client, minds
client._DOTENV_LOADED = True  # never read the real .env in tests
from worldbox.ai.client import ChatResult
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine, SimulationRunner
from worldbox.cli.webview import LiveState

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

calls = []
def fake(**kw):
    calls.append(kw)
    return ChatResult(text=json.dumps({"stance": "farm", "intent": "Grow grain."}), status=200)
minds.chat = fake

cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, min_think_seconds=0.0, max_calls_per_minute=10_000))
eng = SimulationEngine(config=cfg, seed=42)
state = LiveState(eng, SimulationRunner(eng))

def run(days):
    for _ in range(days):
        eng.step(); time.sleep(0.0005)
    time.sleep(0.2); eng.step()

run(800)
before = len(calls)
check("minds call while on", before > 0, before)

r = state.control("ai", "off")
check("control ai off -> paused", r["aiPaused"] is True and eng.minds.paused)
check("toggle event recorded", any("switched off" in e.message for e in eng.events.recent(50)))
pols = len(eng.minds.policies)
run(800)
check("no calls while off", len(calls) == before, f"{before} -> {len(calls)}")
check("policies kept while off", len(eng.minds.policies) >= 1 and pols >= 1, (pols, len(eng.minds.policies)))
check("narrator refused while off", state.explain()["ok"] is False)

r = state.control("ai", "toggle")
check("toggle -> on", r["aiPaused"] is False)
run(800)
check("calls resume when on", len(calls) > before, f"{before} -> {len(calls)}")

r = state.control("ai_cap", "3")
check("runtime cap", r["aiCap"] == 3 and eng.minds.call_cap() == 3)
os.environ["LLM_MAX_CALLS_PER_MINUTE"] = "9"
check("runtime cap beats .env", eng.minds.call_cap() == 3)
r = state.control("ai_cap", "")
check("empty cap -> back to .env", r["aiCap"] == 9, r["aiCap"])
os.environ.pop("LLM_MAX_CALLS_PER_MINUTE")

check("LLM plays at most 3 tribes by default", eng.minds.mind_slots() == 3 and len(eng.minds.policies) <= 3, (eng.minds.mind_slots(), len(eng.minds.policies)))
check("/state marks managed tribes", {c["id"] for c in state.snapshot()["civs"] if c["llm"]} == set(eng.minds.managed_ids()))
r = state.control("ai_minds", "1")
check("runtime tribe count", r["aiMinds"] == 1)
eng.step()
check("tribes outside the count go back to the rules", len(eng.minds.policies) <= 1, len(eng.minds.policies))
os.environ["LLM_MAX_MINDS"] = "2"
state.control("ai_minds", "")
check("empty count -> back to .env", eng.minds.mind_slots() == 2)
os.environ.pop("LLM_MAX_MINDS")
check("no .env -> config default", eng.minds.mind_slots() == 3)
run(400)
check("never more than the count", len(eng.minds.policies) <= 3, len(eng.minds.policies))

r = state.control("ai_forget", None)
check("forget drops policies", r.get("forgotten", 0) >= 1 and not eng.minds.policies, r)

eng.reset(7)
check("switches survive a world reset", eng.minds.call_cap() == cfg.ai.max_calls_per_minute and eng.minds.paused is False)
state.control("ai", "off"); eng.reset(8)
check("paused survives a world reset", eng.minds.paused is True)

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
