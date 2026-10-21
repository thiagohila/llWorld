"""Arthur's own HUD and server, end to end over real HTTP. No LLM, no network beyond localhost.

Run from the llWorld root:  .venv/bin/python -I -B tests/arthur/test_server.py "$PWD/arthur"
"""
import http.client, json, os, re, sys, time
sys.path.insert(0, sys.argv[1])
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
    os.environ.pop(k, None)
import run as arthur_run  # arthur/run.py
from worldbox.ai import client
client._DOTENV_LOADED = True  # never read the real .env in tests

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

engine, runner, game, arthur = arthur_run.build(seed=42, no_ai=True, port=18765, arthur_port=18866)
arthur_run.start(game, arthur)
port = arthur.port
runner.set_delay(0.01); runner.start()

def req(method, path, body=None, token=None, host=None, origin=None, p=None):
    p = p or port
    conn = http.client.HTTPConnection("127.0.0.1", p, timeout=10)
    headers = {"Host": host or f"127.0.0.1:{p}"}
    if token is not None: headers["X-Arthur-Token"] = token
    if origin is not None: headers["Origin"] = origin
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    r = conn.getresponse(); raw = r.read(); conn.close()
    try: return r.status, json.loads(raw or b"{}")
    except ValueError: return r.status, raw.decode("utf-8", "replace")

try:
    check("two servers on separate ports", arthur.port != game.port and arthur.game_url.endswith(f":{game.port}/"), (game.port, arthur.port))
    status, page = req("GET", "/")
    token = re.search(r'TOKEN="([^"]+)"', page).group(1)
    check("Arthur's page carries its own token", status == 200 and token != "__ARTHUR_TOKEN__" and token != getattr(game.state, "token", None))
    check("Arthur's page frames the game map", arthur.game_url in page and "__GAME_URL__" not in page)

    check("state needs the token", req("GET", "/api/state")[0] == 403)
    status, st = req("GET", "/api/state", token=token)
    check("state reads the world", status == 200 and st["world"]["population"] > 0 and "llm" in st, st.get("world"))

    send = "/api/send"
    origin = f"http://127.0.0.1:{port}"
    check("send without token -> 403", req("POST", send, {"text": "oi"})[0] == 403)
    check("send with wrong token -> 403", req("POST", send, {"text": "oi"}, token="nope")[0] == 403)
    check("other Host (DNS rebinding) -> 403", req("POST", send, {"text": "oi"}, token=token, host=f"evil.example:{port}")[0] == 403)
    check("other Origin (CSRF) -> 403", req("POST", send, {"text": "oi"}, token=token, origin="https://evil.example")[0] == 403)
    check("game's map Origin cannot post to Arthur", req("POST", send, {"text": "oi"}, token=token, origin=f"http://127.0.0.1:{game.port}")[0] == 403)
    check("oversized body -> 413", req("POST", send, b"{" + b" " * 20000 + b"}", token=token, origin=origin)[0] == 413)

    status, r = req("POST", send, {"text": "Majestade, fortaleça as defesas do norte."}, token=token, origin=origin)
    check("valid send accepted", status == 200 and r.get("ok"), r)
    reply = None
    for _ in range(40):
        _, msgs = req("GET", "/api/messages?since=-1", token=token)
        done = [m for m in msgs["messages"] if m["role"] == "character" and not m["pending"]]
        if done: reply = done[-1]; break
        time.sleep(0.05)
    check("the king's stand-in answers", reply is not None and "(teste)" in reply["text"], reply)
    _, later = req("GET", "/api/messages?since=%d" % reply["id"], token=token)
    check("since filters old messages", later["messages"] == [])

    _, r = req("POST", "/api/llm", {"value": "off"}, token=token, origin=origin)
    check("Arthur's HUD flips the shared LLM switch", r.get("paused") is True and engine.minds.paused is True)
    req("POST", send, {"text": "Está me ouvindo?"}, token=token, origin=origin)
    _, msgs = req("GET", "/api/messages?since=%d" % reply["id"], token=token)
    check("king stays silent while LLM is off", any(m["role"] == "system" and "desligadas" in m["text"] for m in msgs["messages"]))
    _, r = req("POST", "/api/llm", {"value": "on"}, token=token, origin=origin)
    check("switch back on", r.get("paused") is False)

    # --- LLMs tab: sources, purposes, consumption, switches ---------------
    check("LLM report needs the token", req("GET", "/api/llm/report")[0] == 403)
    os.environ.update(LLM_BASE_URL="https://api.example.test/v1", LLM_MODEL="model-x", LLM_API_KEY="supersecret-key-123")
    from worldbox.ai import narrator
    from worldbox.ai.client import ChatResult
    narrator.chat = lambda **kw: ChatResult(text="Uma história.", status=200, tokens_in=50, tokens_out=20)
    from worldbox.simulation.chronicle import ChronicleEntry, Milestone
    narrator.narrate([ChronicleEntry(day=1, year=0, kind=Milestone.TRIBE, message="x")])
    status, rep = req("GET", "/api/llm/report", token=token)
    ids = [p["id"] for p in rep["purposes"]]
    check("report lists the four purposes", ids == ["tribes", "narrator", "arthur_chat", "arthur_council"], ids)
    check("report maps the configured source", any(s["house"] == "custom" and s["configured"] and s["host"] == "api.example.test" for s in rep["sources"]), rep["sources"])
    check("report never contains a key", "supersecret-key-123" not in json.dumps(rep))
    nar = next(p for p in rep["purposes"] if p["id"] == "narrator")
    check("narrator consumption counted", nar["usage"]["calls"] == 1 and nar["usage"]["tokens_in"] == 50, nar["usage"])
    chat = next(p for p in rep["purposes"] if p["id"] == "arthur_chat")
    check("Arthur's chat shows no LLM use yet", chat["usage"]["calls"] == 0 and chat["usage"]["messages"] >= 2, chat["usage"])
    check("total sums the purposes", rep["total"]["calls"] == sum(p["usage"].get("calls", 0) for p in rep["purposes"]) and rep["total"]["tokens_in"] >= 50)
    _, r = req("POST", "/api/llm", {"target": "arthur_chat", "value": "off"}, token=token, origin=origin)
    check("Arthur's own switch", r.get("enabled") is False and arthur.advisor.llm_enabled is False)
    _, before = req("GET", "/api/messages?since=-1", token=token)
    req("POST", send, {"text": "E agora?"}, token=token, origin=origin)
    _, msgs = req("GET", "/api/messages?since=%d" % before["messages"][-1]["id"], token=token)
    check("chat off -> the king stays silent", any(m["role"] == "system" and "aba LLMs" in m["text"] for m in msgs["messages"]), msgs["messages"])
    check("chat switch does not touch the master", engine.minds.paused is False)
    req("POST", "/api/llm", {"target": "arthur_chat", "value": "on"}, token=token, origin=origin)
    _, r = req("POST", "/api/llm/cap", {"value": 4}, token=token, origin=origin)
    check("cap from Arthur's HUD", r.get("cap") == 4 and engine.minds.call_cap() == 4)
    _, r = req("POST", "/api/llm/minds", {"value": 2}, token=token, origin=origin)
    check("tribe count from Arthur's HUD", r.get("max_minds") == 2 and engine.minds.mind_slots() == 2)
    _, rep = req("GET", "/api/llm/report", token=token)
    tp = next(p for p in rep["purposes"] if p["id"] == "tribes")
    check("report shows managed/max tribes", tp["slots"]["max"] == 2, tp.get("slots"))
    req("POST", "/api/llm/minds", {"value": ""}, token=token, origin=origin)
    check("unknown LLM target rejected", req("POST", "/api/llm", {"target": "nope", "value": "off"}, token=token, origin=origin)[1].get("ok") is False)
    for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"): os.environ.pop(k)

    check("game map still served on its own port", req("GET", "/state?since=-1", p=game.port)[0] == 200)
    check("game HUD has no Arthur tab (no extension registered)", game.state.extensions == {})
    check("unknown Arthur route -> 404", req("GET", "/api/nope", token=token)[0] == 404)
finally:
    runner.pause(); arthur.stop(); game.stop()

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
