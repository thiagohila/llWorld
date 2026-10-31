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
fork_minds.chat = lambda **kw: ChatResult(text=json.dumps({"stance": "farm", "intent": "Grow grain."}), status=200)
council_calls = []
def fake_council(**kw):
    council_calls.append(kw)
    return ChatResult(text=json.dumps({"policy": {"stance": "farm", "intent": "Fill the granaries.", "farmer_share": 0.5},
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

# --- budget, quota gate (shared with the council), switches ------------------------------------------
answer["result"] = None
minds._recent_calls.clear()
before = len(minds._recent_calls)
send("Conta?")
check("a message counts against the shared per-minute budget", len(minds._recent_calls) == before + 1)
minds._cap_override = 0
n = len(voice_calls)
_, msgs = send("Teto?")
check("budget full: no call, panel says so", len(voice_calls) == n and any("teto" in m["text"] for m in msgs if m["role"] == "system"), msgs)
minds._cap_override = None

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
