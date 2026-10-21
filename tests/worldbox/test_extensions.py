"""The game's generic extension routes (/ext), with a throwaway echo extension. No LLM.

Run from the llWorld root:  .venv/bin/python -I -B tests/worldbox/test_extensions.py "$PWD/worldbox"
"""
import dataclasses, http.client, json, re, sys
sys.path.insert(0, sys.argv[1])
from worldbox.config import Config
from worldbox.simulation.engine import SimulationEngine, SimulationRunner
from worldbox.cli.webview import LiveServer

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: fails.append(name)

class Echo:
    id = "echo"
    def describe(self): return {"title": "Echo", "kind": "chat"}
    def handle(self, action, payload):
        if action == "boom": raise RuntimeError("secret detail")
        return {"ok": True, "action": action, "payload": payload}

cfg = Config(); cfg = dataclasses.replace(cfg, ai=dataclasses.replace(cfg.ai, enabled=False))
engine = SimulationEngine(config=cfg, seed=42); runner = SimulationRunner(engine)
server = LiveServer(engine, runner, port=18965)
server.add_extension(Echo()); server.start(); port = server.port

def req(method, path, body=None, token=None, host=None, origin=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Host": host or f"127.0.0.1:{port}"}
    if token is not None: headers["X-Worldbox-Token"] = token
    if origin is not None: headers["Origin"] = origin
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    r = conn.getresponse(); raw = r.read(); conn.close()
    try: return r.status, json.loads(raw or b"{}")
    except ValueError: return r.status, raw.decode("utf-8", "replace")

try:
    _, page = req("GET", "/")
    token = re.search(r'WB_TOKEN="([^"]+)"', page).group(1)
    check("page carries a session token", token != "__WB_TOKEN__")
    check("manifest needs the token", req("GET", "/ext")[0] == 403)
    check("manifest lists the extension", any(x["id"] == "echo" for x in req("GET", "/ext", token=token)[1]["extensions"]))
    check("POST without token -> 403", req("POST", "/ext/echo/send", {"a": 1})[0] == 403)
    check("other Host -> 403", req("POST", "/ext/echo/send", {"a": 1}, token=token, host=f"evil.example:{port}")[0] == 403)
    check("other Origin -> 403", req("POST", "/ext/echo/send", {"a": 1}, token=token, origin="https://evil.example")[0] == 403)
    check("oversized body -> 413", req("POST", "/ext/echo/send", b"{" + b" " * 20000 + b"}", token=token)[0] == 413)
    s, r = req("POST", "/ext/echo/send", {"a": 1}, token=token, origin=f"http://127.0.0.1:{port}")
    check("valid POST reaches the extension", s == 200 and r["payload"] == {"a": 1} and r["action"] == "send", r)
    s, r = req("GET", "/ext/echo/messages?since=3", token=token)
    check("GET passes the query", r["payload"] == {"since": "3"}, r)
    s, r = req("POST", "/ext/echo/boom", {}, token=token)
    check("extension errors do not leak details", r.get("ok") is False and "secret" not in json.dumps(r), r)
    check("original routes unchanged", req("GET", "/state?since=-1")[0] == 200)
    try:
        server.add_extension(type("Bad", (), {"id": "Bad Id!"})()); check("bad id rejected", False)
    except ValueError:
        check("bad id rejected", True)
finally:
    server.stop()

print("\nRESULT:", "all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
