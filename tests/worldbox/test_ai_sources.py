"""Offline checks for the .env-configured house and the mock mind. No network."""
import dataclasses, io, json, os, sys, time
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "LLM_LABEL", "LLM_MAX_CALLS_PER_MINUTE"):
    os.environ.pop(k, None)
from worldbox.ai import client, minds
client._DOTENV_LOADED = True  # never read the real .env in tests
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine
fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

sent = []
class Resp(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): pass
def fake(req, timeout=None, context=None):
    sent.append((req.full_url, dict(req.header_items()), json.loads(req.data)))
    return Resp(json.dumps({"choices": [{"message": {"content": '{"stance":"farm"}'}}]}).encode())
def no_network(*a, **k):
    raise AssertionError("network used")

# H. Nothing configured -> no minds.
check("H nothing configured: not available", not client.is_available())

# I. Groq-style house with a key.
os.environ.update(LLM_BASE_URL="https://api.groq.com/openai/v1", LLM_MODEL="llama-3.3-70b-versatile", LLM_API_KEY="dummy", LLM_LABEL="Groq Llama")
client.urllib.request.urlopen = fake
spec = client.house_spec("custom")
check("I custom: available and labelled", client.is_available() and spec["label"] == "Groq Llama", spec)
r = client.chat([{"role": "user", "content": "x"}], model="custom", max_tokens=450, json_mode=True)
url, headers, body = sent[-1]
check("I custom: posts to /chat/completions", url == "https://api.groq.com/openai/v1/chat/completions", url)
check("I custom: bearer auth", headers.get("Authorization") == "Bearer dummy")
check("I custom: generic params", body.get("max_tokens") == 450 and "temperature" in body and "thinking" not in body, list(body))
check("I custom: ok", r.ok, r.error)

# J. Local Ollama: no key -> no Authorization header.
os.environ.pop("LLM_API_KEY"); os.environ.update(LLM_BASE_URL="http://127.0.0.1:11434/v1", LLM_MODEL="qwen2.5:3b")
r = client.chat([{"role": "user", "content": "x"}], model="custom", max_tokens=450)
url, headers, body = sent[-1]
check("J ollama: keyless still available", client.is_available())
check("J ollama: no Authorization header", "Authorization" not in headers, headers)
check("J ollama: local url", url == "http://127.0.0.1:11434/v1/chat/completions", url)

# K. Mock minds: a full engine run plays tribes with zero network.
os.environ.pop("LLM_MODEL"); os.environ["LLM_BASE_URL"] = "mock"
client.urllib.request.urlopen = no_network
cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, min_think_seconds=0.0))
eng = SimulationEngine(config=cfg, seed=42)
for _ in range(2500):
    eng.step(); time.sleep(0.0005)
time.sleep(0.2); eng.step()
pols = eng.minds.policies
stances = sorted({p.stance for p in pols.values()})
inv = [p.invent.name for p in pols.values() if p.invent]
u = eng.minds.usage_snapshot()
check("K mock: policies applied without network", len(pols) > 0 and u["failures"] == 0, (len(pols), u))
from worldbox.ai import mock
hungry = mock.decide("You are the mind of the A (tribe_id 1).\nPeople: 20. Hunger: 70/100.")
at_war = mock.decide("You are the mind of the A (tribe_id 1).\nPeople: 20. Hunger: 10/100.\n  tribe_id 2 B: 40 people, Camp, Stone Age, relation -80, 3 tiles AT WAR.")
calm = mock.decide("You are the mind of the A (tribe_id 1).\nPeople: 12. Hunger: 10/100.")
check("K mock: stance follows the situation", (hungry["stance"], at_war["stance"], calm["stance"]) == ("farm", "defend", "expand"),
      (hungry["stance"], at_war["stance"], calm["stance"]))
check("K mock: houses labelled", eng.minds.snapshot(eng)[0].model.startswith("Mock"), eng.minds.snapshot(eng)[0].model)
print("   mock inventions in progress:", inv[:4], "| stances:", stances)

# L. Calls-per-minute override from .env.
os.environ["LLM_MAX_CALLS_PER_MINUTE"] = "4"
check("L cap override", eng.minds.call_cap() == 4, eng.minds.call_cap())

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
