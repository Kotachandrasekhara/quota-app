"""The local web server and its JSON API, and the entry point."""
import json
import platform
import re
import sys
import threading
import time
import webbrowser
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config
from .budget import away_secs, away_type, budgets, set_days_off, workday_set
from .categories import category_names
from .config import APP_NAME, DATA_FILE, DEFAULT_CONFIG, DEMO, OFFLINE_KINDS, OFF_TYPES, lock, state
from .demo import seed_demo
from .offline import add_offline, offline_view, remove_offline
from .reports import export_csv, history, parse_range
from .settings import apply_config, text_fields, validate_config
from .status import compute_status, fmt
from .store import init, DATA, save
from .system import idle_seconds, notify
from .tracker import tracker
from .icon import png
from .web import PAGES


# ---------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_ok(self):
        # only accept requests aimed at the local dashboard (blocks other websites and DNS rebinding)
        ok_hosts = (f"127.0.0.1:{config.PORT}", f"localhost:{config.PORT}")
        if self.headers.get("Host", "") not in ok_hosts:
            return False
        origin = self.headers.get("Origin")
        return not origin or origin in tuple(f"http://{h}" for h in ok_hosts)

    def _send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_POST(self):
        if (self.path not in ("/api/config", "/api/days-off", "/api/pause", "/api/offline", "/api/test-notify")
                or not self._host_ok()
                or "application/json" not in self.headers.get("Content-Type", "")):
            return self._json(403, {"error": "forbidden"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 60000:
                raise ValueError("Request too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
        except (ValueError, TypeError) as e:
            return self._json(400, {"error": str(e)})
        if self.path == "/api/offline":  # work away from the computer: in-person meetings, org events
            try:
                day = date.fromisoformat(str(payload.get("date")))
            except ValueError:
                return self._json(400, {"error": "Date must look like 2026-11-05"})
            if abs((day - date.today()).days) > 1100:
                return self._json(400, {"error": "Pick a date within three years of today"})
            if payload.get("remove"):
                with lock:
                    gone = remove_offline(day.isoformat(), str(payload["remove"]))
                    if gone:
                        apply_config({})
                return self._json(200 if gone else 404, {"removed": gone} if gone else {"error": "No such entry"})
            start, kind = str(payload.get("start", "")), payload.get("kind")
            if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", start):
                return self._json(400, {"error": "Start time must look like 09:30"})
            try:
                mins = int(float(payload.get("minutes")))
            except (TypeError, ValueError):
                return self._json(400, {"error": "Length must be a number of minutes"})
            if not 5 <= mins <= 720:
                return self._json(400, {"error": "Length must be between 5 minutes and 12 hours"})
            if int(start[:2]) * 60 + int(start[3:]) + mins > 1440:
                return self._json(400, {"error": "That block runs past midnight. Split it into two days"})
            if kind not in OFFLINE_KINDS:
                return self._json(400, {"error": "Kind must be meeting, event, training or other"})
            cat = str(payload.get("category") or "Meetings")
            if cat not in category_names() + ["Other"]:
                cat = "Other"
            note = "".join(ch for ch in str(payload.get("note") or "") if ch.isprintable()).strip()[:60]
            with lock:
                if len(DATA["offline"].get(day.isoformat(), [])) >= 20:
                    return self._json(400, {"error": "That day already has 20 entries"})
                add_offline(day.isoformat(), start, mins, kind, cat, note)
                apply_config({})
                result = {"status": compute_status()}
            return self._json(200, result)
        if self.path == "/api/test-notify":
            notify("Quota test reminder", "If you can see this, reminders work on this computer.")
            return self._json(200, {"ok": True, "platform": platform.system()})
        if self.path == "/api/pause":  # Private mode: in memory only, so it is off whenever Quota starts
            want = payload.get("paused")
            if not isinstance(want, bool):
                return self._json(400, {"error": "paused must be true or false"})
            state["paused"] = want
            state["paused_at"] = time.time() if want else None
            if want:
                state["active"] = False
                state["now_app"], state["now_cat"] = None, None
            return self._json(200, {"paused": want})
        if self.path == "/api/days-off":
            try:
                start = date.fromisoformat(str(payload.get("from")))
                end = date.fromisoformat(str(payload.get("to", payload.get("from"))))
            except ValueError:
                return self._json(400, {"error": "Dates must look like 2026-11-05"})
            kind = payload.get("type")
            if kind == "none":
                kind = None
            elif kind not in OFF_TYPES:
                return self._json(400, {"error": "Type must be holiday, leave, sick or none"})
            if start > end:
                return self._json(400, {"error": "'from' must not be after 'to'"})
            if (end - start).days > 366:
                return self._json(400, {"error": "Pick at most 367 days at a time"})
            today = date.today()
            if abs((start - today).days) > 1100 or abs((end - today).days) > 1100:
                return self._json(400, {"error": "Pick dates within three years of today"})
            away = None
            if payload.get("hours") not in (None, "", 0) and kind:
                try:
                    hours = float(payload["hours"])
                except (TypeError, ValueError):
                    return self._json(400, {"error": "Hours must be a number like 2 or 1.5"})
                if not 0.25 <= hours <= 24:
                    return self._json(400, {"error": "Hours away must be between 0.25 and 24"})
                if hours * 3600 >= budgets()[0]:
                    return self._json(400, {"error": "That is the whole working day. Choose 'Whole day' instead"})
                away = int(round(hours * 3600))
            with lock:
                changed = set_days_off(start, end, kind, bool(payload.get("workdays_only", True)), away)
                apply_config({})  # re-checks warnings against the new budget and saves
                result = {"changed": changed, "status": compute_status()}
            return self._json(200, result)
        try:
            cfg = validate_config(payload)
        except (ValueError, TypeError) as e:
            return self._json(400, {"error": str(e)})
        with lock:
            apply_config(cfg)
            result = {"config": dict(DATA["config"]), "status": compute_status()}
        self._json(200, result)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/") and not self._host_ok():
            return self._json(403, {"error": "forbidden"})
        qs = parse_qs(parsed.query)
        if path == "/api/config":
            with lock:
                return self._json(200, dict(DATA["config"], **text_fields(DATA["config"])))
        if path == "/api/defaults":
            return self._json(200, text_fields(DEFAULT_CONFIG))
        if path == "/api/status":
            with lock:
                return self._json(200, compute_status())
        if path == "/api/pause":
            return self._json(200, {"paused": state["paused"], "since": state["paused_at"]})
        if path == "/api/offline":
            with lock:
                cut = (date.today() - timedelta(days=60)).isoformat()
                items = [{"date": k, "entries": offline_view(k)} for k in sorted(DATA["offline"], reverse=True)
                         if k >= cut and DATA["offline"][k]]
                return self._json(200, {"items": items, "kinds": OFFLINE_KINDS})
        if path == "/api/days-off":
            with lock:
                return self._json(200, {"off": {k: v for k, v in DATA["off"].items() if v in OFF_TYPES},
                                        "part": {k: {"type": away_type(k), "hours": round(away_secs(k) / 3600, 2)}
                                                 for k in DATA["part"] if away_secs(k)},
                                        "types": OFF_TYPES, "workdays": sorted(workday_set())})
        if path in ("/api/history", "/api/export.csv"):
            try:
                start, end = parse_range(qs)
            except ValueError as err:
                return self._json(400, {"error": str(err)})
            if path == "/api/history":
                with lock:
                    return self._json(200, history(start, end))
            kind = qs.get("kind", [""])[0]
            kind = kind if kind in ("apps", "domains") else "days"
            with lock:
                body = export_csv(start, end, kind).encode("utf-8-sig")  # BOM so Excel reads UTF-8
            return self._send(200, body, "text/csv; charset=utf-8",
                              {"Content-Disposition": f'attachment; filename="quota-{kind}-{start}_{end}.csv"'})
        if path in ("/icon.png", "/icon-192.png"):  # the app icon, for "Add to Dock" and "Install as app"
            return self._send(200, png(512 if path == "/icon.png" else 192), "image/png",
                              {"Cache-Control": "max-age=86400"})
        if path == "/manifest.webmanifest":
            manifest = {"name": "Quota", "short_name": "Quota", "start_url": "/", "scope": "/", "display": "standalone",
                        "background_color": "#f2f2f2", "theme_color": "#6250d6",
                        "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                                  {"src": "/icon.png", "sizes": "512x512", "type": "image/png"}]}
            return self._send(200, json.dumps(manifest).encode(), "application/manifest+json")
        page = PAGES.get(path)
        if page is None:
            return self._json(404, {"error": "not found"})
        self._send(200, page.encode(), "text/html; charset=utf-8")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("install", "uninstall"):
        from . import autostart
        sys.exit(autostart.run(sys.argv[1]))
    init()
    if DEMO and not DATA["days"]:
        seed_demo()
    save(DATA)
    daily, weekly = budgets()
    print(f"{APP_NAME} running. Weekly budget: {weekly:,} tokens ({fmt(weekly)}); daily: {fmt(daily)}.")
    print(f"Open: http://127.0.0.1:{config.PORT}   Data: {DATA_FILE}")
    if idle_seconds() is None:
        state["idle_supported"] = False
        print("Note: idle detection is unavailable on this system, so all running time is counted. "
              "On Linux, install `xprintidle` for idle detection.")
    threading.Thread(target=tracker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", config.PORT), Handler)
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{config.PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with lock:
            save(DATA)
        print("Saved. Bye.")
