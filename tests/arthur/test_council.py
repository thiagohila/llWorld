"""Arthur's council (stage 3): the king decides his realm's policy. No network:
both the council's and the tribe minds' calls go to fakes.

Run from the llWorld root:  .venv/bin/python -I -B tests/arthur/test_council.py "$PWD/arthur"
"""
import dataclasses, json, os, sys, time
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY",
          "LLM_LABEL", "LLM_MAX_CALLS_PER_MINUTE", "LLM_MAX_MINDS"):
    os.environ.pop(k, None)
os.environ.update(LLM_BASE_URL="https://llm.example.test/v1", LLM_MODEL="fake-model",
                  LLM_API_KEY="dummy-not-a-key", LLM_LABEL="Fake")
import run as arthur_run  # arthur/run.py
from worldbox.ai import client, minds as fork_minds
client._DOTENV_LOADED = True  # never read the real .env in tests
from worldbox.ai.client import ChatResult
from arthur import council as council_mod

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

# --- fakes ---------------------------------------------------------------------
tribe_calls = []
def fake_tribes(**kw):
    tribe_calls.append(kw)
    return ChatResult(text=json.dumps({"stance": "farm", "intent": "Grow grain."}), status=200)
fork_minds.chat = fake_tribes

king_calls = []
answer = {"text": None, "result": None}
def decision(stance="farm", intent="Fill the granaries.", rationale="Celeiro primeiro.", **policy):
    policy.setdefault("warrior_share", 0.6)
    return json.dumps({"policy": dict(stance=stance, intent=intent, farmer_share=0.2, **policy), "rationale": rationale})
def fake_king(**kw):
    king_calls.append(kw)
    if answer["result"] is not None:
        return answer["result"]
    return ChatResult(text=answer["text"] or decision(), status=200, tokens_in=300, tokens_out=60)
council_mod.chat = fake_king

engine, runner, game, arthur = arthur_run.build(seed=42, no_ai=False, port=18765, arthur_port=18866)
kingdom = arthur.kingdom
council = kingdom.council
minds = engine.minds
minds.config = dataclasses.replace(minds.config, min_think_seconds=0.0, max_calls_per_minute=10_000)
interval = minds.config.think_interval_days

def settle():
    """Let a call in flight come back and be applied."""
    for _ in range(200):
        if not council.pending:
            break
        time.sleep(0.005)
    engine.step()

def days(n):
    for _ in range(n):
        engine.step()
        if council.pending:
            settle()

realm = kingdom.group

# --- first thought -------------------------------------------------------------
engine.step(); settle()
check("thinks on the first day", len(king_calls) == 1 and council.policy is not None, len(king_calls))
check("policy applied with rationale", council.policy.stance == "farm" and council.rationale == "Celeiro primeiro.")
sent = king_calls[0]["messages"]
check("persona in the system prompt", "Arthur Pendragon" in sent[0]["content"] and "red lines" in sent[0]["content"])
check("report of his own realm", "tribe_id %d" % realm.id in sent[1]["content"])
check("uses the .env source", king_calls[0]["model"] == "custom")
check("engine sees it through policy_for", minds.policy_for(realm.id) is council.policy)
check("same object every time (engine edits it)", minds.policy_for(realm.id) is minds.policy_for(realm.id))
check("not in the tribes' table", realm.id not in minds.policies and realm.id not in minds.managed_ids())
check("decision logged and narrated", council.log[0]["stance"] == "farm"
      and any("King Arthur chose to farm" in e.message for e in engine.events.recent(50)))
check("usage counted", council.usage["calls"] == 1 and council.usage["tokens_in"] == 300)

# --- the policy acts on the world ------------------------------------------------
days(3)
adults = sum(n for r, n in realm.role_counts.items() if r != "child")
check("roles follow the policy (60% warriors)", realm.role_counts.get("warrior", 0) >= adults * 0.4, realm.role_counts)

# --- cadence -------------------------------------------------------------------
before, logged = len(king_calls), len(council.log)
days(interval // 2)
early = [d["reason"] for d in list(council.log)[: len(council.log) - logged]]
check("within the interval only triggers call", len(king_calls) - before <= 1 and "interval" not in early, early)
answer["text"] = decision("research", "Learn the river's ways.", "Celeiro cheio; hora de aprender.")
council.signature = None  # the situation counts as new
days(interval)
check("thinks again after the interval", len(king_calls) > before and council.policy.stance == "research", council.policy.stance)

# --- shared budget and switches ---------------------------------------------------
minds.set_call_cap(0)
council.policy = None  # would trigger at once
before = len(king_calls)
days(3)
check("shared budget spent: no call", len(king_calls) == before)
minds.set_call_cap(None)
minds.config = dataclasses.replace(minds.config, max_calls_per_minute=10_000)
days(2)
check("calls again when budget frees", len(king_calls) > before and council.policy is not None)

minds.set_paused(True)
before, kept = len(king_calls), council.policy
council.signature = None; council.last_day -= interval
days(interval + 2)
check("master switch off: no calls", len(king_calls) == before)
check("master switch off: policy keeps acting", minds.policy_for(realm.id) is kept)
minds.set_paused(False)
council.enabled = False
days(interval + 2)
check("own switch off: no calls", len(king_calls) == before)
council.enabled = True

# --- triggers -------------------------------------------------------------------
other = next(g for g in engine.groups.active() if g is not realm)
before = len(king_calls)
council.last_day = engine.clock.day - council_mod.MIN_TRIGGER_DAYS  # thought 10 days ago
engine.diplomacy.adjust(realm.id, other.id, -500)
from worldbox.society.diplomacy import pair_key, War
engine.diplomacy.wars[pair_key(realm.id, other.id)] = War(tribes=pair_key(realm.id, other.id), started_day=engine.clock.day)
days(2)
check("a new war makes him think early", len(king_calls) == before + 1, len(king_calls) - before)

# --- validation -------------------------------------------------------------------
peaceful = next(g for g in engine.groups.active() if g is not realm and g is not other)
engine.diplomacy.adjust(realm.id, peaceful.id, 30 - engine.diplomacy.relation(realm.id, peaceful.id))
answer["text"] = decision("raid", "Strike them all.", "Atacar.",
                          toward=[{"tribe_id": peaceful.id, "action": "war"}, {"tribe_id": other.id, "action": "war"},
                                  {"tribe_id": 9999, "action": "trade"}])
council.policy = None
days(2)
pol = council.policy
check("red line: no war on a peaceful people", (peaceful.id, "war") not in pol.toward and (other.id, "war") in pol.toward, pol.toward)
check("unknown tribe dropped", all(tid != 9999 for tid, _ in pol.toward))
check("red-line veto credited to the king", any(v["by"] == "king" and "unprovoked" in v["text"] for v in council.log[0]["vetoes"]), council.log[0]["vetoes"])
check("unknown tribe credited to the game", any(v["by"] == "game" and "9999" in v["text"] for v in council.log[0]["vetoes"]))
rel = engine.diplomacy.relation(realm.id, other.id)
days(3)
check("toward moves relations (war pushes down)", engine.diplomacy.relation(realm.id, other.id) < rel)

engine.diplomacy.wars.clear()
for g in engine.groups.active():
    if g is not realm:
        engine.diplomacy.adjust(realm.id, g.id, 10 - engine.diplomacy.relation(realm.id, g.id))
answer["text"] = decision("raid", "Raid someone.", "Atacar alguém.")
council.policy = None
days(2)
check("raid with no enemy becomes defend", council.policy.stance == "defend", council.policy.stance)

kept = council.policy
for bad in ("{}", "not json at all", json.dumps({"policy": {}, "rationale": "x"})):
    answer["text"] = bad
    council.signature = None; council.last_day -= interval; council.retry_day = -1; council.retry_wall = 0
    days(2)
    check(f"bad reply {bad[:12]!r} keeps the previous policy", council.policy is kept and council.error)
answer["text"] = json.dumps({"stance": "farm", "intent": "Flat answer.", "farmer_share": 0.4})
council.signature = None; council.last_day -= interval; council.retry_day = -1; council.retry_wall = 0
days(2)
check("flat JSON (the mock's shape) accepted", council.policy.intent == "Flat answer." and council.rationale == "Flat answer.")

# --- colonies are the king's decision ----------------------------------------------------
from arthur.bridge import settle_people
from arthur.kingdom import KING as KING_MARK
split = engine.config.groups.split_size
answer["text"] = json.dumps({"policy": {"stance": "farm", "intent": "Stay together."}, "found_colony": True, "rationale": "x"})
small = realm.size < split
council.signature = None; council.last_day -= interval; council.retry_day = -1; council.retry_wall = 0
days(2)
if small:
    check("colony refused while the kingdom is small", any(v["by"] == "game" and "colony" in v["text"] for v in council.log[0]["vetoes"]), council.log[0]["vetoes"])
settle_people(engine, realm, kingdom.king.x, kingdom.king.y, split + 20 - realm.size, "Pendragon", houses=[""])
days(3)
check("big kingdom does not split by itself", engine.groups.get(realm.id) is realm and realm.size >= split, realm.size)
check("report tells him he may found a colony", "found a colony" in council._messages()[1]["content"])
before_groups = {g.id for g in engine.groups.active()}
size_before = realm.size
answer["text"] = json.dumps({"policy": {"stance": "expand", "intent": "Settle the far hills."}, "found_colony": True, "rationale": "Colônia."})
council.signature = None; council.last_day -= interval; council.retry_day = -1; council.retry_wall = 0
days(4)
new = [g for g in engine.groups.active() if g.id not in before_groups and g.parent_group_id == realm.id]
check("ordered colony is founded", len(new) >= 1 and realm.size < size_before, (len(new), size_before, realm.size))
check("king stays home", kingdom.king.group_id == realm.id and realm.chieftain_id == kingdom.king.id)
if new:
    check("colony starts friendly", engine.diplomacy.relation(realm.id, new[0].id) > 0, engine.diplomacy.relation(realm.id, new[0].id))
    check("colony narrated", any("sent" in e.message and "found the" in e.message for e in engine.events.recent(200)))
check("one order, one colony", not getattr(realm, "llworld_colony_order", False))
setattr(realm, "llworld_colony_order", True)  # an order the realm is too small to carry out
if realm.size < split:
    days(2)
    check("an order that cannot be carried out lapses", not getattr(realm, "llworld_colony_order", False)
          and any("did not set out" in e.message for e in engine.events.recent(100)))
else:
    setattr(realm, "llworld_colony_order", False)
check("decision log marks the order", any(d.get("colony") for d in council.log))

# --- the craft limit is told, so he stops asking ---------------------------------------
known = realm.knowledge.known
fake = {f"custom_test_{i}" for i in range(engine.config.ai.max_custom_techs)}
check("no limit line while under it", "unique crafts allowed" not in council._messages()[1]["content"])
known.update(fake)
check("limit reached: report tells him", "unique crafts allowed" in council._messages()[1]["content"])
known.difference_update(fake)

# --- quota spent (429): wait on the gate, longer each time ---------------------------
gate = council.quota
check("the king waits on the game's gate (same key as the tribes)", gate is minds.quota)
clock = [1000.0]
gate._clock = lambda: clock[0]
quota_spent = lambda **kw: tribe_calls.append(kw) or ChatResult(error="API returned 429: quota exceeded", status=429)
fork_minds.chat = quota_spent  # the provider refuses everyone
answer["result"] = ChatResult(error="API returned 429: quota exceeded", status=429)
council.policy = None; council.retry_day = -1; council.retry_wall = 0
before = len(king_calls)
days(2)
check("a 429 closes the gate", not gate.open() and council.status() == "quota" and gate.retry_in() == 60,
      (council.status(), gate.retry_in()))
council.retry_day = -1; council.retry_wall = 0  # only the gate holds him now
asked = len(king_calls)
tribes_asked = len(tribe_calls)
days(interval * 3)
check("the tribes do not call either while it is closed", len(tribe_calls) == tribes_asked, (tribes_asked, len(tribe_calls)))
check("no calls while the gate is closed", len(king_calls) == asked and asked == before + 1, (before, asked, len(king_calls)))
cp = next(p for p in arthur.llm_report()["purposes"] if p["id"] == "arthur_council")
check("LLMs tab says he waits for the quota", "429" in cp["state"] and "1 min" in cp["state"], cp["state"])
check("HUD gets the wait", arthur.state()["council"]["retryIn"] == 60)
clock[0] += 61
council.retry_day = -1; council.retry_wall = 0
days(2)
check("tries again after the wait; a second 429 waits longer",
      len(king_calls) == asked + 1 and gate.retry_in() == 300, (len(king_calls), gate.retry_in()))
answer["result"] = None
clock[0] += 301
council.retry_day = -1; council.retry_wall = 0
days(2)
check("an answer reopens the gate", gate.open() and gate.strikes == 0 and council.policy is not None
      and council.status() != "quota")
gate._clock = time.monotonic
fork_minds.chat = fake_tribes

# --- forget, fatal, reset -----------------------------------------------------------
r = game.state.control("ai_forget", None)
check("map's forget also drops his policy", council.policy is None and r.get("forgotten", 0) >= 1, r)
answer["result"] = ChatResult(error="401 bad key", status=401)
days(2)
check("fatal error halts every mind", bool(minds.halted) and council.status() == "halted", minds.halted)
answer["result"] = None
minds.halted = ""

answer["text"] = decision("expand", "Old world.", "Mundo velho.")
council.policy = None; council.retry_day = -1; council.retry_wall = 0
engine.step()  # asks; the answer arrives after the reset
check("call in flight", council.pending)
engine.reset(7)
time.sleep(0.2); engine.step()
check("stale answer dropped after reset", all(d["intent"] != "Old world." for d in council.log) and kingdom.group is not realm)
answer["text"] = decision()
days(2)
check("new realm gets its own decision", council.realm is kingdom.group and council.policy is not None)

# --- the tribes keep their slots ------------------------------------------------------
days(interval)
check("tribe minds still use their own slots", 0 < len(minds.managed_ids()) <= minds.mind_slots()
      and kingdom.group.id not in minds.managed_ids())
report = arthur.llm_report()
cp = next(p for p in report["purposes"] if p["id"] == "arthur_council")
check("LLMs tab shows his use", cp["usage"]["calls"] == council.usage["calls"] and cp["control"] == "própria")
check("LLMs tab: own switch", arthur.set_llm("off", "arthur_council")["enabled"] is False and council.enabled is False)
arthur.set_llm("on", "arthur_council")
check("state carries the council", arthur.state()["council"]["policy"] is not None)
runner.pause()

# --- --no-ai: nothing at all -------------------------------------------------------------
king_calls.clear()
e2, r2, g2, a2 = arthur_run.build(seed=42, no_ai=True, port=18765, arthur_port=18866)
for _ in range(60): e2.step()
check("--no-ai: the king never calls", king_calls == [] and a2.kingdom.council.policy is None)

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
