import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

from tests import support

from quota import config, server, store


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        config.PORT = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.data = support.reset()
        config.state["paused"] = False

    def call(self, method, path, body=None, headers=None, ctype="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", config.PORT, timeout=5)
        h = {"Content-Type": ctype}
        h.update(headers or {})
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read().decode("utf-8-sig")
        conn.close()
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, raw

    def test_pages_render(self):
        for path in ("/", "/reports", "/settings", "/history"):
            code, html = self.call("GET", path)
            self.assertEqual(code, 200, path)
            self.assertNotIn("%%", html)

    def test_app_icon_and_manifest(self):
        conn = http.client.HTTPConnection("127.0.0.1", config.PORT, timeout=10)
        conn.request("GET", "/icon.png")
        r = conn.getresponse()
        self.assertEqual((r.status, r.read()[:4]), (200, b"\x89PNG"))
        conn.close()
        code, manifest = self.call("GET", "/manifest.webmanifest")
        self.assertEqual((code, manifest["name"]), (200, "Quota"))
        self.assertIn("/manifest.webmanifest", self.call("GET", "/")[1])

    def test_other_websites_and_hosts_are_refused(self):
        self.assertEqual(self.call("POST", "/api/pause", {"paused": True}, {"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.call("POST", "/api/pause", {"paused": True}, ctype="text/plain")[0], 403)
        self.assertEqual(self.call("GET", "/api/status", headers={"Host": "evil.example:8765"})[0], 403)
        self.assertEqual(self.call("POST", "/api/tab", {})[0], 403)  # the removed extension endpoint stays closed

    def test_private_mode_toggle_and_validation(self):
        self.assertEqual(self.call("POST", "/api/pause", {"paused": True})[1], {"paused": True})
        self.assertTrue(self.call("GET", "/api/status")[1]["paused"])
        self.assertEqual(self.call("POST", "/api/pause", {"paused": False})[1], {"paused": False})
        self.assertEqual(self.call("POST", "/api/pause", {"paused": "yes"})[0], 400)

    def test_days_off(self):
        code, j = self.call("POST", "/api/days-off", {"from": "2026-11-10", "type": "leave", "hours": 2,
                                                       "workdays_only": False})
        self.assertEqual((code, j["changed"]), (200, 1))
        self.assertEqual(self.call("GET", "/api/days-off")[1]["part"]["2026-11-10"], {"type": "leave", "hours": 2.0})
        for body in ({"from": "nope", "type": "leave"}, {"from": "2026-11-09", "type": "party"},
                     {"from": "2026-11-12", "to": "2026-11-09", "type": "leave"},
                     {"from": "2026-11-10", "type": "leave", "hours": 99},
                     {"from": "2026-11-10", "type": "leave", "hours": 8},
                     {"from": "2040-01-01", "type": "leave"}):
            self.assertEqual(self.call("POST", "/api/days-off", body)[0], 400, body)
        self.call("POST", "/api/days-off", {"from": "2026-11-10", "type": "none"})
        self.assertEqual(self.call("GET", "/api/days-off")[1]["part"], {})

    def test_offline_blocks(self):
        day = "2026-11-03"
        code, _ = self.call("POST", "/api/offline", {"date": day, "start": "13:30", "minutes": 90, "kind": "meeting",
                                                      "category": "Meetings", "note": "Visit <b>"})
        self.assertEqual(code, 200)
        item = self.call("GET", "/api/offline")[1]["items"][0]
        self.assertEqual(item["entries"][0]["note"], "Visit <b>")  # stored as text; the pages show it as text
        self.assertEqual(self.call("POST", "/api/offline", {"date": day, "remove": item["entries"][0]["id"]})[0], 200)
        self.assertEqual(self.call("POST", "/api/offline", {"date": day, "remove": "nope"})[0], 404)
        for body in ({"start": "23:30", "minutes": 90}, {"start": "9am", "minutes": 30}, {"start": "09:00", "minutes": 2},
                     {"start": "09:00", "minutes": 30, "kind": "party"}):
            body = dict({"date": day, "kind": "meeting"}, **body)
            self.assertEqual(self.call("POST", "/api/offline", body)[0], 400, body)

    def test_csv_cannot_run_formulas(self):
        self.data["apps"]["2026-11-03"] = {"=cmd|calc": 60}
        code, text = self.call("GET", "/api/export.csv?kind=apps&from=2026-11-03&to=2026-11-03")
        self.assertEqual(code, 200)
        self.assertIn("'=cmd|calc", text)

    def test_test_reminder(self):
        with mock.patch("quota.server.notify") as n:
            self.assertEqual(self.call("POST", "/api/test-notify", {})[0], 200)
        n.assert_called_once()

    def test_settings_roundtrip(self):
        cfg = self.call("GET", "/api/config")[1]
        cfg["daily_hours"] = 6
        self.assertEqual(self.call("POST", "/api/config", cfg)[0], 200)
        self.assertEqual(store.DATA["config"]["daily_hours"], 6)
        cfg["daily_hours"] = 99
        self.assertEqual(self.call("POST", "/api/config", cfg)[0], 400)


if __name__ == "__main__":
    unittest.main()
