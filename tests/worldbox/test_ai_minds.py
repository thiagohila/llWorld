"""Offline checks for the AI cost/robustness changes. No network: chat/urlopen are faked."""
import dataclasses, io, json, os, sys, time, urllib.error
sys.path.insert(0, sys.argv[1])
os.environ.pop("OPENAI_API_KEY", None); os.environ["DEEPSEEK_API_KEY"] = "dummy-not-a-key"
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine
from worldbox.ai import minds, client, narrator
client._DOTENV_LOADED = True  # never read the real .env in tests
from worldbox.ai.client import ChatResult

POLICY = json.dumps({"stance": "farm", "farmer_share": 0.4, "intent": "Grow grain."})
fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

def engine_with(fake, **ai):
    minds.chat = fake
    cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, **ai))
    return SimulationEngine(config=cfg, seed=42)

def run(eng, days, settle=0.0):
    for _ in range(days):
        eng.step()
        if settle: time.sleep(settle)
    time.sleep(0.3); eng.step()  # let worker threads land, then drain

# A. Healthy minds, real-time throttle off: calls happen, policies apply, tokens counted.
calls = []
def ok(**kw):
    calls.append(kw); return ChatResult(text=POLICY, model="deepseek-flash", status=200, tokens_in=900, tokens_out=120)
eng = engine_with(ok, min_think_seconds=0.0, max_calls_per_minute=10_000)
run(eng, 2500, settle=0.0005)
u = eng.minds.usage_snapshot()
check("A healthy: calls made", u["calls"] > 0, u)
check("A healthy: policies applied", len(eng.minds.policies) > 0)
check("A healthy: tokens counted", u["tokens_in"] == 900 * len(calls) or u["tokens_in"] > 0)
check("A healthy: no flavour/model line in briefing", all("Your model is" not in c["messages"][1]["content"] for c in calls))
check("A healthy: deepseek budget 450", all(c["max_tokens"] == 450 for c in calls))
check("A healthy: some calls skipped as unchanged", u["skipped"] > 0, f"skipped={u['skipped']}")

# B. Real-time throttle on (defaults): a fast headless run makes few calls.
calls.clear()
eng = engine_with(ok)
t0 = time.monotonic(); run(eng, 2500); took = time.monotonic() - t0
import re as _re, collections as _c, math as _m
per_tribe = _c.Counter(_re.search(r"tribe_id (\d+)", c["messages"][1]["content"]).group(1) for c in calls)
allowed = _m.ceil(took / eng.config.ai.min_think_seconds)
check("B throttle: per tribe <= run seconds / min_think_seconds", max(per_tribe.values()) <= allowed,
      f"run {took:.0f}s, allowed {allowed}, max {max(per_tribe.values())}, total {len(calls)} (without it: ~{2500 // eng.config.ai.think_interval_days} per tribe)")

# C. Rate limited (429): backoff, not a call per tribe per day.
calls.clear()
def limited(**kw):
    calls.append(kw); return ChatResult(error="API returned 429", status=429)
eng = engine_with(limited, min_think_seconds=0.0, max_calls_per_minute=10_000, failure_backoff_seconds=0.0)
run(eng, 2500, settle=0.0005)
u = eng.minds.usage_snapshot()
tribes_seen = len({1}) and u["failures"]
check("C backoff: failures counted", u["failures"] == u["calls"] > 0, u)
check("C backoff: far fewer calls than days x tribes", u["calls"] < 200, u["calls"])

# D. Bad key (401): minds halt after the first batch.
calls.clear()
def rejected(**kw):
    calls.append(kw); return ChatResult(error="API rejected the key (401)", status=401)
eng = engine_with(rejected, min_think_seconds=0.0, max_calls_per_minute=10_000)
run(eng, 400, settle=0.0005); first = len(calls)
run(eng, 1500, settle=0.0005)
check("D fatal: halted", bool(eng.minds.halted), eng.minds.halted)
check("D fatal: no calls after halting", len(calls) == first, f"{first} -> {len(calls)}")

# E. Empty JSON policy is rejected, not applied.
def empty(**kw): return ChatResult(text="{}", status=200)
eng = engine_with(empty, min_think_seconds=0.0, max_calls_per_minute=10_000)
run(eng, 1500, settle=0.0005)
check("E empty policy rejected", not eng.minds.policies and eng.minds.usage["failures"] > 0)

# F. Client: OpenAI reasoning payload and one adaptive resend on a 400.
sent = []
class Resp(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): pass
def fake_urlopen(req, timeout=None, context=None):
    body = json.loads(req.data); sent.append((req.full_url, body))
    if len(sent) == 1:
        raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(b'{"error":{"message":"Unsupported value: \'reasoning_effort\' does not support minimal"}}'))
    return Resp(json.dumps({"choices": [{"message": {"content": POLICY}}], "usage": {"prompt_tokens": 800, "completion_tokens": 90, "prompt_tokens_details": {"cached_tokens": 512}}}).encode())
client.urllib.request.urlopen = fake_urlopen
r = client.chat([{"role": "user", "content": "x"}], key="dummy", model="gpt-5-mini", max_tokens=900, reasoning_effort="minimal", json_mode=True)
first_body = sent[0][1]
check("F openai: max_completion_tokens, no max_tokens", "max_completion_tokens" in first_body and "max_tokens" not in first_body, list(first_body))
check("F openai: no temperature for gpt-5", "temperature" not in first_body)
check("F openai: resent once without reasoning_effort", len(sent) == 2 and "reasoning_effort" not in sent[1][1])
check("F openai: result ok with usage", r.ok and r.tokens_in == 800 and r.tokens_cached == 512, (r.ok, r.tokens_in, r.tokens_cached))

# G. Narrator works with only an OpenAI key (falls back to the OpenAI house).
sent.clear(); os.environ.pop("DEEPSEEK_API_KEY"); os.environ["OPENAI_API_KEY"] = "dummy-not-a-key"
def ok_urlopen(req, timeout=None, context=None):
    sent.append((req.full_url, json.loads(req.data)))
    return Resp(json.dumps({"choices": [{"message": {"content": "A short history."}}]}).encode())
client.urllib.request.urlopen = ok_urlopen
from worldbox.simulation.chronicle import ChronicleEntry, Milestone
n = narrator.narrate([ChronicleEntry(day=1, year=0, kind=Milestone.TRIBE, message="A tribe formed")])
check("G narrator with OpenAI only", n.ok and sent and "openai.com" in sent[0][0], (n.error, sent[0][0] if sent else None))

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
