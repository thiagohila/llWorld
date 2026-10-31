"""Arthur's voice (stage 4a): the king answers his advisor. No network: the
voice's, the council's and the tribe minds' calls all go to fakes.

Run from the llWorld root:  .venv/bin/python -I -B tests/arthur/test_voice.py "$PWD/arthur"
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
from arthur import council as council_mod, voice as voice_mod

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

# --- fakes ---------------------------------------------------------------------
tribe_calls = []
fork_minds.chat = lambda **kw: tribe_calls.append(1) or ChatResult(text=json.dumps({"stance": "farm", "intent": "Grow grain."}), status=200)
council_calls = []
council_answer = {"followed": [], "result": None}
def fake_council(**kw):
    council_calls.append(kw)
    if council_answer["result"] is not None:
        return council_answer["result"]
    return ChatResult(text=json.dumps({"policy": {"stance": "farm", "intent": "Fill the granaries.", "farmer_share": 0.5},
                                       "advice_followed": council_answer["followed"],
                                       "rationale": "Celeiro primeiro."}), status=200)
council_mod.chat = fake_council

voice_calls = []
answer = {"result": None}
def said(reply, advice=None):
    return ChatResult(text=json.dumps({"reply": reply, "advice": advice}), status=200, tokens_in=400, tokens_out=50)
def fake_voice(**kw):
    voice_calls.append(kw)
    return answer["result"] or said("Ouço-te, conselheiro.")
voice_mod.chat = fake_voice

engine, runner, game, arthur = arthur_run.build(seed=42, no_ai=False, port=18765, arthur_port=18866)
kingdom, advisor = arthur.kingdom, arthur.advisor
council, minds = kingdom.council, engine.minds
minds.config = dataclasses.replace(minds.config, min_think_seconds=0.0, max_calls_per_minute=10_000)

def settle_council():
    for _ in range(200):
        if not council.pending:
            break
        time.sleep(0.005)
    engine.step()

def send(text):
    """Send, wait for the reply, return the messages it produced."""
    last = advisor.handle("messages", {})["messages"][-1]["id"]
    r = advisor.handle("send", {"text": text})
    for _ in range(400):
        if not advisor._busy:
            break
        time.sleep(0.005)
    return r, advisor.handle("messages", {"since": last})["messages"]

for _ in range(3): engine.step(); settle_council()
check("the council decided first", council.policy is not None and council.log)
check("live greeting", "Fale com o Rei Arthur" in advisor.handle("messages", {})["messages"][0]["text"])

# --- a plain exchange ------------------------------------------------------------------
policy_before, council_before = council.policy, len(council_calls)
answer["result"] = said("Camelot está em paz, conselheiro.")
r, msgs = send("Como está o reino?")
king = [m for m in msgs if m["role"] == "character"]
check("the king answers in his words", r["ok"] and king and king[-1]["text"] == "Camelot está em paz, conselheiro."
      and king[-1]["advice"] is None, msgs)
call = voice_calls[-1]
system = call["messages"][0]["content"]
check("persona in the prompt", "Arthur Pendragon" in system and "red lines" in system and "Portuguese" in system)
check("his realm's report in the prompt", f"tribe_id {kingdom.group.id}" in system and "Report (day " in system
      and "Granary" in system)
check("the decision-only lines are left out", "You may set" not in system and "You are the mind" not in system
      and "Your kingdom: the Kingdom of Arthur" in system)
check("his recent decisions and reasons", "Your recent decisions" in system and "Celeiro primeiro." in system)
check("the message is the last turn", call["messages"][-1] == {"role": "user", "content": "Como está o reino?"})
check("uses the council's source, JSON mode", call["model"] == "custom" and call["json_mode"] is True)
check("talking changes nothing", council.policy is policy_before and len(council_calls) == council_before)
use = advisor.usage_snapshot()
check("usage counted", use["llm_calls"] == 1 and use["tokens_in"] == 400 and use["replies"] == 1 and use["uses_llm"], use)

# --- history: earlier turns, only the last few -----------------------------------------------
send("E os vizinhos?")
turns = voice_calls[-1]["messages"][1:-1]
check("earlier exchange goes along", turns[:2] == [{"role": "user", "content": "Como está o reino?"},
                                                   {"role": "assistant", "content": "Camelot está em paz, conselheiro."}], turns[:2])
for i in range(8): send(f"pergunta {i}")
turns = voice_calls[-1]["messages"][1:-1]
check("only the last 6 exchanges", len(turns) == 12 and turns[-2]["content"] == "pergunta 6", len(turns))

# --- advice and his verdict -------------------------------------------------------------------
answer["result"] = said("Não farei guerra a quem vive em paz conosco.",
                        {"summary": "atacar os vizinhos", "verdict": "reject", "urgent": True})
_, msgs = send("Ataque os vizinhos agora!")
reply = [m for m in msgs if m["role"] == "character"][-1]
check("advice read, rejected", reply["advice"] == {"summary": "atacar os vizinhos", "verdict": "reject", "urgent": False}, reply["advice"])
answer["result"] = said("Pensarei nisso.", {"summary": "plantar mais", "verdict": "consider", "urgent": True})
_, msgs = send("Plante mais, o inverno vem.")
check("urgent advice kept when considered", [m for m in msgs if m["role"] == "character"][-1]["advice"]["urgent"] is True)
answer["result"] = said("Hm.", {"summary": "x", "verdict": "maybe"})
_, msgs = send("Faça algo.")
check("unknown verdict dropped", [m for m in msgs if m["role"] == "character"][-1]["advice"] is None)
answer["result"] = ChatResult(text="Sim, conselheiro, ouvi.", status=200)
_, msgs = send("Ouviu?")
check("plain text (format ignored) still answers", [m for m in msgs if m["role"] == "character"][-1]["text"] == "Sim, conselheiro, ouvi.")

# --- failures: he needs time, the panel says why ------------------------------------------------
answer["result"] = ChatResult(text="{broken", status=200)
failures = advisor.usage["failures"]
_, msgs = send("Ei?")
check("unusable answer: fallback in character + note", any(m["role"] == "character" and m["text"] == voice_mod.FALLBACK for m in msgs)
      and any(m["role"] == "system" and "LLM falhou" in m["text"] for m in msgs) and advisor.usage["failures"] == failures + 1, msgs)
answer["result"] = ChatResult(error="API returned 503", status=503)
_, msgs = send("Ei?")
check("call error: same fallback", any(m["text"] == voice_mod.FALLBACK for m in msgs))

# --- stage 4b: advice he did not turn down reaches his next decision -------------------------------
def days(n):
    for _ in range(n):
        engine.step()
        if council.pending:
            settle_council()

council.advice.clear(); council.urgent = False
interval = minds.config.think_interval_days
days(interval + 1)  # a fresh decision, so the next one is a while away
check("prompt shape asks which advice he follows", "advice_followed" in council._messages()[0]["content"])
check("no counsel line without advice", "advisor's counsel" not in council._messages()[1]["content"])
answer["result"] = said("Não.", {"summary": "atacar os vizinhos", "verdict": "reject", "urgent": False})
send("Ataque!")
check("rejected advice is not kept", council.advice == [])
answer["result"] = said("Pensarei.", {"summary": "plantar mais trigo", "verdict": "consider", "urgent": False})
send("Plante mais trigo.")
answer["result"] = said("Sim.", {"summary": "fazer paz com os vizinhos", "verdict": "accept", "urgent": False})
send("Faça paz com os vizinhos.")
check("considered and accepted advice kept", [a["summary"] for a in council.advice] == ["plantar mais trigo", "fazer paz com os vizinhos"])
check("HUD lists the advice waiting", len(arthur.state()["council"]["advice"]) == 2)
report = council._messages()[1]["content"]
ids = [a["id"] for a in council.advice]
check("report carries the counsel, his words and his verdict", f"[{ids[0]}]" in report and "Plante mais trigo." in report
      and "you would consider it" in report and "you agreed" in report, report[-400:])
council_answer["followed"] = [ids[1], "a999"]
n = len(council_calls)
days(interval + 1)
check("he thought on his usual day", len(council_calls) > n)
entry = council.log[0]
check("log says which advice he followed", entry["advice"] == [{"summary": "plantar mais trigo", "followed": False},
                                                              {"summary": "fazer paz com os vizinhos", "followed": True}], entry.get("advice"))
check("weighed advice is consumed", council.advice == [])
council_answer["followed"] = []

for i in range(5):
    answer["result"] = said("Pensarei.", {"summary": f"ideia {i}", "verdict": "consider", "urgent": False})
    send(f"ideia {i}")
check("only the last 3 pieces wait", [a["summary"] for a in council.advice] == ["ideia 2", "ideia 3", "ideia 4"])
days(interval + 1)
council.advice.clear()

# urgent advice brings the council forward, but not within 10 days of the last
n = len(council_calls)
while len(council_calls) == n:  # right after a decision
    days(1)
last = council.last_day
answer["result"] = said("Agora mesmo pensarei.", {"summary": "defender o celeiro", "verdict": "accept", "urgent": True})
send("Proteja o celeiro, já!")
check("urgent advice flags the council", council.urgent and council._situation()[0] == "urgent advice")
n = len(council_calls)
days(council_mod.MIN_TRIGGER_DAYS - 2)
check("not before the minimum gap", len(council_calls) == n)
days(4)
check("then he thinks early, for the advice", len(council_calls) == n + 1 and council.log[0]["reason"] == "urgent advice"
      and engine.clock.day - last < interval, (council.log[0]["reason"], engine.clock.day - last))
check("urgency cleared once weighed", not council.urgent and council.advice == [])

answer["result"] = said("Pensarei.", {"summary": "algo urgente", "verdict": "consider", "urgent": True})
send("Urgente!")
council_answer["result"] = ChatResult(error="API returned 503", status=503)
days(council_mod.MIN_TRIGGER_DAYS + 1)
check("a failed council keeps the advice and its urgency", council.advice and council.urgent)
council_answer["result"] = None
council.retry_day = -1; council.retry_wall = 0
days(council_mod.MIN_TRIGGER_DAYS + 1)
check("and weighs it once the call works", council.advice == [] and council.log[0]["reason"] == "urgent advice")

# an answer that lands after the world was reset is not heard
gen = council.generation
call = kingdom.council and arthur.advisor.voice.snapshot([])
council.generation += 1
answer["result"] = said("Sim.", {"summary": "velho mundo", "verdict": "accept", "urgent": True})
arthur.advisor.voice.answer("Velho?", call)
check("advice about a reset world is dropped", council.advice == [] and not council.urgent)
council.generation = gen
answer["result"] = None

# --- budget, quota gate (shared with the council), switches ------------------------------------------
answer["result"] = None
minds._recent_calls.clear()
before = len(minds._recent_calls)
send("Conta?")
check("a message counts against the shared per-minute budget", len(minds._recent_calls) == before + 1)
minds._cap_override = 0
n = len(voice_calls)
_, msgs = send("Teto?")
check("cap at zero: no call, panel says so", len(voice_calls) == n and any("teto" in m["text"] for m in msgs if m["role"] == "system"), msgs)

# budget busy (tribes and council use it too): the message waits for a slot
voice = advisor.voice
minds._cap_override = 1
minds._recent_calls.clear(); minds._recent_calls.append(time.monotonic())
last = advisor.handle("messages", {})["messages"][-1]["id"]
advisor.handle("send", {"text": "Espera?"})
time.sleep(0.4)
waiting = advisor.handle("messages", {"since": last})["messages"]
check("busy budget: the message waits (pending), no call yet", len(voice_calls) == n and any(m["pending"] for m in waiting), waiting)
check("the panel says the message is queued", any(m["role"] == "system" and "fila" in m["text"] for m in waiting), waiting)
check("meanwhile the others see one slot less (the player goes first)", minds.call_cap() == 0 and voice._cap() == 1)
t = len(tribe_calls)
with runner.lock:  # the message's thread cannot grab the slot while we look
    minds._recent_calls.popleft()  # a slot frees up...
    for _ in range(minds.config.think_interval_days * 2): engine.step()
    check("tribe minds really yield that slot to the waiting message", len(tribe_calls) == t and voice._waiting == 1,
          (t, len(tribe_calls)))
    minds._recent_calls.append(time.monotonic())
minds._cap_override = None  # room frees up
for _ in range(400):
    if not advisor._busy: break
    time.sleep(0.005)
msgs = advisor.handle("messages", {"since": last})["messages"]
check("slot reservation released", minds.call_cap() == voice._cap())
check("then he answers", len(voice_calls) == n + 1 and any(m["role"] == "character" and not m["pending"] for m in msgs), msgs)
voice.budget_wait = 0.3
minds._cap_override = 1
minds._recent_calls.clear(); minds._recent_calls.append(time.monotonic())
calls_before = advisor.usage["llm_calls"]
_, msgs = send("Ainda cheio?")
check("budget full for the whole wait: panel says so, no call", len(voice_calls) == n + 1
      and advisor.usage["llm_calls"] == calls_before and any(m["role"] == "system" and "teto" in m["text"] for m in msgs), msgs)
minds._cap_override = None
voice.budget_wait = voice_mod.BUDGET_WAIT

answer["result"] = ChatResult(error="API returned 429: quota exceeded", status=429)
_, msgs = send("Cota?")
check("a 429 closes the shared gate", not council.quota.open() and council.status() == "quota")
n = len(voice_calls)
_, msgs = send("E agora?")
check("gate closed: no call, panel says when", len(voice_calls) == n and any("429" in m["text"] for m in msgs if m["role"] == "system"), msgs)
rep = next(p for p in arthur.llm_report()["purposes"] if p["id"] == "arthur_chat")
check("LLMs tab: chat waits for the quota", "429" in rep["state"], rep["state"])
council.quota.until = 0.0; council.quota.strikes = 0
answer["result"] = None

minds.paused = True
n = len(voice_calls)
_, msgs = send("Oi?")
check("master switch off: silent", len(voice_calls) == n and any("botão AI" in m["text"] for m in msgs))
minds.paused = False
advisor.llm_enabled = False
_, msgs = send("Oi?")
check("own switch off: silent", len(voice_calls) == n and any("aba LLMs" in m["text"] for m in msgs))
advisor.llm_enabled = True

answer["result"] = ChatResult(error="API rejected the key (401)", status=401)
send("Chave?")
check("fatal error halts every mind", bool(minds.halted))
n = len(voice_calls)
_, msgs = send("De novo?")
check("halted: no call", len(voice_calls) == n and any("pararam" in m["text"] for m in msgs))
minds.halted = ""
answer["result"] = None

rep = next(p for p in arthur.llm_report()["purposes"] if p["id"] == "arthur_chat")
check("LLMs tab shows the chat's use", rep["usage"]["calls"] == advisor.usage["llm_calls"] > 0 and rep["model"] == "Fake", rep)
runner.pause()

# --- --no-ai: the stand-in, no calls ------------------------------------------------------------
voice_calls.clear()
e2, r2, g2, a2 = arthur_run.build(seed=42, no_ai=True, port=18765, arthur_port=18866)
a2.advisor.handle("send", {"text": "Oi?"})
for _ in range(400):
    if not a2.advisor._busy: break
    time.sleep(0.005)
last = a2.advisor.handle("messages", {})["messages"][-1]
check("--no-ai: stand-in answers, no call", voice_calls == [] and "(sem LLM)" in last["text"], last)

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
