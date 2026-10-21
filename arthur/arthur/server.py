"""Arthur's own server: its HUD and API, beside the game's live map.

It runs in the same process as the game, on its own port (default 8766), and
reads the world straight from the engine under the game's lock. The game's
server and HUD are untouched; Arthur's page shows the game map in a frame.

Every ``/api`` call is guarded: the Host must be this server (DNS
rebinding), a POST's Origin must be this page (CSRF), and the session token
must come in the ``X-Arthur-Token`` header -- a foreign page cannot send it
without a CORS preflight this server never answers. Bodies are capped.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .bridge import EventKind, all_houses, available_houses, llm_available, narrator

PAGE_FILE = Path(__file__).resolve().parent / "static" / "index.html"
MAX_BODY = 16 * 1024


class ArthurServer:
    """Serves Arthur's HUD and its JSON API while the world runs."""

    def __init__(self, engine: Any, runner: Any, advisor: Any, game_url: str, port: int = 8766) -> None:
        self.engine = engine
        self.runner = runner
        self.advisor = advisor
        self.game_url = game_url
        self.port = port
        self.token = secrets.token_urlsafe(18)
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    # -- what the HUD reads and does -------------------------------------------

    def state(self) -> Dict[str, Any]:
        """World summary and LLM status for Arthur's HUD."""
        with self.runner.lock:
            stats = self.engine.stats()
            minds = self.engine.minds
            usage = minds.usage_snapshot()
            world = {
                "day": stats.day,
                "year": stats.year,
                "era": stats.most_advanced_era,
                "population": stats.population,
                "tribes": stats.tribes,
                "wars": stats.active_wars,
                "running": self.runner.running,
            }
        return {
            "ok": True,
            "world": world,
            "llm": {
                "available": bool(self.engine.config.ai.enabled and llm_available()),
                "paused": usage["paused"],
                "halted": usage["halted"],
                "calls": usage["calls"],
                "perMinute": usage["per_minute"],
                "cap": usage["cap"],
            },
            "gameUrl": self.game_url,
        }

    def set_llm(self, value: str, target: str = "all") -> Dict[str, Any]:
        """Switch LLM use on/off: ``all`` is the game's master switch (tribes,
        narrator and Arthur); ``arthur_chat`` is Arthur's own, for the
        conversation only. The master switch always wins."""
        choice = (value or "toggle").strip().lower()
        if target == "arthur_chat":
            advisor = self.advisor
            advisor.llm_enabled = (choice == "on") if choice in ("on", "off") else not advisor.llm_enabled
            return {"ok": True, "target": target, "enabled": advisor.llm_enabled}
        if target != "all":
            return {"ok": False, "error": f"Unknown LLM target '{target}'."}
        minds = self.engine.minds
        minds.set_paused(choice == "off" if choice in ("on", "off") else not minds.paused)
        with self.runner.lock:
            self.engine.events.record(
                self.engine.clock.day, EventKind.SYSTEM,
                "LLM calls switched " + ("off" if minds.paused else "on") + " (Arthur)",
            )
        return {"ok": True, "target": target, "paused": minds.paused}

    def set_cap(self, value: Any) -> Dict[str, Any]:
        """Per-minute ceiling for the tribe minds (empty = back to .env/config)."""
        minds = self.engine.minds
        if value in (None, ""):
            minds.set_call_cap(None)
        else:
            try:
                minds.set_call_cap(max(0, min(120, int(float(value)))))
            except (TypeError, ValueError):
                return {"ok": False, "error": "Cap must be a number."}
        return {"ok": True, "cap": minds.call_cap()}

    def llm_report(self) -> Dict[str, Any]:
        """Every LLM source and every purpose that uses one, with consumption.

        Never includes a key: only which sources have one configured.
        """
        with self.runner.lock:
            minds = self.engine.minds
            mind_use = minds.usage_snapshot()
            rows = minds.snapshot(self.engine)
            minds_on = bool(self.engine.config.ai.enabled)
        paused, halted = mind_use["paused"], mind_use["halted"]
        usable = available_houses()
        usable_keys = {(s["house"], s["model"]) for s in usable}
        tribes_by_house = Counter(r.house for r in rows if r.house)
        # The narrator asks for the default house and falls back to the first usable one.
        narrator_source = next((s for s in usable if s["house"] == "deepseek"), usable[0] if usable else None)

        sources = []
        for spec in all_houses():
            host = urlparse(spec.get("url") or "").netloc or ("offline" if spec["house"] == "mock" else "")
            users = []
            if tribes_by_house.get(spec["house"]):
                users.append(f"mentes de {tribes_by_house[spec['house']]} tribo(s)")
            if narrator_source and (narrator_source["house"], narrator_source["model"]) == (spec["house"], spec["model"]):
                users.append("narrador")
            sources.append({
                "house": spec["house"], "label": spec["label"], "model": spec["model"], "host": host,
                "configured": (spec["house"], spec["model"]) in usable_keys,
                "keyless": bool(spec.get("keyless")), "users": users,
            })

        def master_state(extra_off: Optional[str] = None) -> str:
            if not usable:
                return "sem fonte de LLM"
            if halted:
                return "parado: " + halted
            if paused:
                return "desligado (interruptor geral)"
            return extra_off or "ligado"

        tribe_models = sorted({r.model for r in rows if r.model})
        nar = narrator.usage_snapshot()
        chat = self.advisor.usage_snapshot()
        purposes = [
            {
                "id": "tribes", "name": "Mentes das tribos", "where": "jogo",
                "what": "decidem a política de cada tribo: profissões, diplomacia, invenções",
                "model": ", ".join(tribe_models) or "—",
                "state": master_state(None if minds_on else "desligado (--no-ai)"),
                "control": "geral",
                "usage": {"calls": mind_use["calls"], "skipped": mind_use["skipped"], "failures": mind_use["failures"],
                          "tokens_in": mind_use["tokens_in"], "tokens_out": mind_use["tokens_out"],
                          "tokens_cached": mind_use["tokens_cached"], "per_minute": mind_use["per_minute"]},
            },
            {
                "id": "narrator", "name": "Narrador (Ask AI)", "where": "jogo",
                "what": "escreve a história do mundo a partir da crônica, quando você pede",
                "model": narrator_source["label"] if narrator_source else "—",
                "state": master_state("ligado (sob demanda)"),
                "control": "geral",
                "usage": nar,
            },
            {
                "id": "arthur_chat", "name": "Conversa do Arthur", "where": "Arthur",
                "what": "o rei responde ao conselheiro",
                "model": chat["model"],
                "state": master_state(None if chat["enabled"] else "desligado (só a conversa)")
                         if chat["uses_llm"] else ("ligado, sem LLM (etapa 1)" if chat["enabled"] else "desligado (só a conversa)"),
                "control": "própria",
                "enabled": chat["enabled"],
                "usage": {"calls": chat["llm_calls"], "failures": chat["failures"], "messages": chat["messages"],
                          "replies": chat["replies"], "tokens_in": chat["tokens_in"], "tokens_out": chat["tokens_out"]},
            },
            {
                "id": "arthur_council", "name": "Decisões do Arthur", "where": "Arthur",
                "what": "o rei decide a política do reino",
                "model": "—", "state": "ainda não existe (etapa 3)", "control": "—", "usage": {},
            },
        ]
        total = {
            "calls": sum(p["usage"].get("calls", 0) for p in purposes),
            "failures": sum(p["usage"].get("failures", 0) for p in purposes),
            "tokens_in": sum(p["usage"].get("tokens_in", 0) for p in purposes),
            "tokens_out": sum(p["usage"].get("tokens_out", 0) for p in purposes),
        }
        return {
            "ok": True,
            "master": {"paused": paused, "halted": halted, "available": bool(usable),
                       "cap": mind_use["cap"], "per_minute": mind_use["per_minute"]},
            "sources": sources, "purposes": purposes, "total": total,
        }

    # -- serving -----------------------------------------------------------------

    def page(self) -> str:
        try:
            text = PAGE_FILE.read_text(encoding="utf-8")
        except OSError:
            return f"<!doctype html><meta charset='utf-8'><p>Missing {PAGE_FILE}</p>"
        return text.replace("__ARTHUR_TOKEN__", self.token).replace("__GAME_URL__", self.game_url)

    def start(self) -> str:
        """Start serving on a background thread; tries the next ports if busy."""
        handler = _handler_factory(self)
        last_error: Optional[OSError] = None
        for offset in range(8):
            try:
                self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port + offset), handler)
                self.port += offset
                break
            except OSError as error:
                last_error = error
        if self.httpd is None:
            raise OSError(f"Could not bind a port near {self.port}: {last_error}")
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="arthur-http", daemon=True)
        self.thread.start()
        return self.url

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


def _handler_factory(app: ArthurServer):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args) -> None:  # noqa: D102
            pass

        def _reply(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
            self._reply(status, json.dumps(payload).encode("utf-8"), "application/json")

        def _local_names(self) -> Tuple[str, ...]:
            port = self.server.server_address[1]
            return (f"127.0.0.1:{port}", f"localhost:{port}")

        def _allowed(self, is_post: bool) -> bool:
            if (self.headers.get("Host") or "").lower() not in self._local_names():
                return False
            origin = self.headers.get("Origin")
            if is_post and origin is not None and origin.lower() not in tuple(
                f"http://{name}" for name in self._local_names()
            ):
                return False
            return hmac.compare_digest(self.headers.get("X-Arthur-Token") or "", app.token)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            try:
                if parsed.path == "/":
                    self._reply(200, app.page().encode("utf-8"), "text/html; charset=utf-8")
                elif not parsed.path.startswith("/api/"):
                    self.send_error(404)
                elif not self._allowed(is_post=False):
                    self._json({"ok": False, "error": "Forbidden."}, status=403)
                elif parsed.path == "/api/state":
                    self._json(app.state())
                elif parsed.path == "/api/messages":
                    self._json(app.advisor.handle("messages", query))
                elif parsed.path == "/api/llm/report":
                    self._json(app.llm_report())
                else:
                    self.send_error(404)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                try:
                    self._json({"ok": False, "error": "Server error."}, status=500)
                except OSError:
                    pass

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if not parsed.path.startswith("/api/"):
                    self.send_error(404)
                    return
                if not self._allowed(is_post=True):
                    self._json({"ok": False, "error": "Forbidden."}, status=403)
                    return
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    self._json({"ok": False, "error": "Request too large."}, status=413)
                    return
                try:
                    payload = json.loads((self.rfile.read(length) if length > 0 else b"{}").decode("utf-8") or "{}")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    payload = None
                if not isinstance(payload, dict):
                    self._json({"ok": False, "error": "Body must be a JSON object."}, status=400)
                    return
                if parsed.path == "/api/send":
                    self._json(app.advisor.handle("send", payload))
                elif parsed.path == "/api/llm":
                    self._json(app.set_llm(str(payload.get("value") or "toggle"), str(payload.get("target") or "all")))
                elif parsed.path == "/api/llm/cap":
                    self._json(app.set_cap(payload.get("value")))
                else:
                    self.send_error(404)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                try:
                    self._json({"ok": False, "error": "Server error."}, status=500)
                except OSError:
                    pass

    return Handler
