import http.client
import json
import os
import stat
import sys
import threading
import unittest
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tests import support

from quota import assistant, config, offline, server, store


class FakeAzure(BaseHTTPRequestHandler):
    """Stands in for Azure OpenAI. `mode` picks the behaviour; `seen` records what K(Qu)ota sent."""
    mode = "stream"
    seen = {}

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeAzure.seen = {"path": self.path, "key": self.headers.get("api-key"), "body": body}
        mode = FakeAzure.mode
        if mode in ("401", "404"):
            data = json.dumps({"error": {"message": "nope"}}).encode()
            self.send_response(int(mode))
        elif mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/steal")
            data = b""
        elif body.get("stream"):
            chunks = [{"choices": []}, {"choices": [{"delta": {"content": "Hello"}}]},
                      {"choices": [{"delta": {"content": " world"}}]}, {"choices": [{"delta": {}, "finish_reason": "stop"}]}]
            data = ("".join("data: %s\n\n" % json.dumps(c) for c in chunks) + "data: [DONE]\n\n").encode()
            self.send_response(200)
        else:
            data = json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()
            self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class AssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.azure = ThreadingHTTPServer(("127.0.0.1", 0), FakeAzure)
        cls.azure_url = "http://127.0.0.1:%d" % cls.azure.server_address[1]
        cls.quota = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        config.PORT = cls.quota.server_address[1]
        for s in (cls.azure, cls.quota):
            threading.Thread(target=s.serve_forever, daemon=True).start()
        assistant.ALLOW_INSECURE_LOCALHOST = True

    @classmethod
    def tearDownClass(cls):
        assistant.ALLOW_INSECURE_LOCALHOST = False
        for s in (cls.azure, cls.quota):
            s.shutdown()
            s.server_close()

    def setUp(self):
        self.data = support.reset()
        FakeAzure.mode, FakeAzure.seen = "stream", {}
        for var in ("QUOTA_AI_KEY", "AZURE_OPENAI_API_KEY"):
            os.environ.pop(var, None)

    def call(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", config.PORT, timeout=10)
        conn.request(method, path, json.dumps(body) if body is not None else None, {"Content-Type": "application/json"})
        r = conn.getresponse()
        raw = r.read().decode()
        conn.close()
        return r.status, raw

    def jcall(self, *a, **k):
        code, raw = self.call(*a, **k)
        return code, json.loads(raw)

    def connect(self, **extra):
        body = {"endpoint": self.azure_url, "deployment": "gpt-test", "key": "sk-test-1234567890"}
        body.update(extra)
        self.assertEqual(self.jcall("POST", "/api/ai", body)[0], 200)

    # ---- settings
    def test_endpoint_parsing(self):
        ok = assistant.parse_endpoint(
            "https://res.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-01")
        self.assertEqual(ok, ("https://res.openai.azure.com", "gpt-4o", "2024-02-01"))
        self.assertEqual(assistant.parse_endpoint("https://res.openai.azure.com/")[0], "https://res.openai.azure.com")
        assistant.ALLOW_INSECURE_LOCALHOST = False
        try:
            for bad in ("", "res.openai.azure.com", "http://res.openai.azure.com", "http://127.0.0.1:5",
                        "https://user:pw@res.openai.azure.com", "ftp://x.com"):
                with self.assertRaises(ValueError, msg=bad):
                    assistant.parse_endpoint(bad)
        finally:
            assistant.ALLOW_INSECURE_LOCALHOST = True

    def test_pasted_url_fills_deployment_and_version(self):
        self.assertEqual(self.jcall("POST", "/api/ai", {
            "endpoint": self.azure_url + "/openai/deployments/my-gpt/chat/completions?api-version=2024-06-01",
            "key": "sk-test-1234567890"})[0], 200)
        view = self.jcall("GET", "/api/ai")[1]
        self.assertEqual((view["deployment"], view["api_version"], view["configured"]), ("my-gpt", "2024-06-01", True))

    def test_the_key_never_comes_back(self):
        self.connect()
        for path in ("/api/ai", "/api/config"):
            self.assertNotIn("sk-test-1234567890", self.call("GET", path)[1], path)
        view = self.jcall("GET", "/api/ai")[1]
        self.assertEqual((view["key_set"], view["key_hint"]), (True, "7890"))
        code, raw = self.call("POST", "/api/config", self.jcall("GET", "/api/config")[1])
        self.assertEqual(code, 200)
        self.assertNotIn("sk-test", raw)
        self.assertEqual(self.data["config"]["ai_key"], "sk-test-1234567890")  # saving other settings keeps it

    def test_empty_key_keeps_and_clear_removes(self):
        self.connect()
        self.connect(key="")
        self.assertTrue(self.data["config"]["ai_key"])
        self.jcall("POST", "/api/ai", {"endpoint": self.azure_url, "deployment": "gpt-test", "clear_key": True})
        self.assertEqual(self.data["config"]["ai_key"], "")
        self.assertFalse(self.jcall("GET", "/api/ai")[1]["configured"])

    def test_bad_settings_are_explained(self):
        for body, text in [({"endpoint": "http://x.openai.azure.com"}, "https"), ({"endpoint": self.azure_url, "deployment": "a b"}, "deployment"),
                           ({"endpoint": self.azure_url, "deployment": "d", "api_version": "latest"}, "API version"),
                           ({"endpoint": self.azure_url, "deployment": "d", "key": "short"}, "API key")]:
            code, j = self.jcall("POST", "/api/ai", body)
            self.assertEqual(code, 400, body)
            self.assertIn(text, j["error"])

    def test_key_from_environment(self):
        os.environ["QUOTA_AI_KEY"] = "env-key-1234567890"
        self.jcall("POST", "/api/ai", {"endpoint": self.azure_url, "deployment": "gpt-test"})
        view = self.jcall("GET", "/api/ai")[1]
        self.assertEqual((view["configured"], view["key_source"]), (True, "environment"))

    @unittest.skipIf(sys.platform == "win32", "file modes work differently on Windows")
    def test_data_file_is_private(self):
        store.save(self.data)
        self.assertEqual(stat.S_IMODE(os.stat(store.DATA_FILE).st_mode) & 0o077, 0)

    # ---- talking to Azure
    def test_connection_test(self):
        self.connect()
        code, j = self.jcall("POST", "/api/ai/test", {})
        self.assertEqual((code, j["reply"]), (200, "OK"))
        self.assertEqual(FakeAzure.seen["key"], "sk-test-1234567890")
        self.assertEqual(FakeAzure.seen["path"],
                         "/openai/deployments/gpt-test/chat/completions?api-version=2024-10-21")

    def test_azure_errors_become_readable(self):
        self.connect()
        for mode, text in (("401", "rejected the key"), ("404", "deployment")):
            FakeAzure.mode = mode
            code, j = self.jcall("POST", "/api/ai/test", {})
            self.assertEqual(code, 502)
            self.assertIn(text, j["error"])

    def test_redirects_are_not_followed(self):
        self.connect()
        FakeAzure.mode = "redirect"
        code, j = self.jcall("POST", "/api/ai/test", {})
        self.assertEqual(code, 502)
        self.assertIn("302", j["error"])

    def test_chat_streams_the_answer(self):
        self.connect()
        code, raw = self.call("POST", "/api/chat", {"messages": [{"role": "user", "content": "How am I doing?"}]})
        self.assertEqual(code, 200)
        lines = [json.loads(x) for x in raw.splitlines() if x.strip()]
        kinds = [x["type"] for x in lines]
        self.assertEqual(kinds[:2], ["RUN_STARTED", "TEXT_MESSAGE_START"])
        self.assertEqual(kinds[-2:], ["TEXT_MESSAGE_END", "RUN_FINISHED"])
        self.assertEqual("".join(x.get("delta", "") for x in lines if x["type"] == "TEXT_MESSAGE_CONTENT"), "Hello world")
        self.assertEqual(len({x.get("messageId") for x in lines if "messageId" in x}), 1)
        sent = FakeAzure.seen["body"]
        self.assertTrue(sent["stream"])
        self.assertEqual([m["role"] for m in sent["messages"]], ["system", "user"])
        self.assertIn("Daily log", sent["messages"][0]["content"])

    def test_chat_error_arrives_in_the_stream(self):
        self.connect()
        FakeAzure.mode = "401"
        code, raw = self.call("POST", "/api/chat", {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(code, 200)
        last = json.loads(raw.splitlines()[-1])
        self.assertEqual(last["type"], "RUN_ERROR")
        self.assertIn("rejected the key", last["message"])

    def test_chat_needs_settings_and_a_question(self):
        self.assertEqual(self.jcall("POST", "/api/chat", {"messages": [{"role": "user", "content": "hi"}]})[0], 400)
        self.connect()
        for bad in ([], [{"role": "assistant", "content": "x"}], [{"role": "system", "content": "x"}], "hi",
                    [{"role": "user", "content": 5}]):
            self.assertEqual(self.jcall("POST", "/api/chat", {"messages": bad})[0], 400, bad)

    def test_long_chats_are_trimmed(self):
        msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": "x" * 5000} for i in range(31)]
        out = assistant.clean_messages(msgs)
        self.assertEqual(len(out), assistant.MAX_MESSAGES)
        self.assertTrue(all(len(m["content"]) == assistant.MAX_CHARS for m in out))

    # ---- what the model sees
    def test_context_has_the_numbers_but_not_titles_or_websites(self):
        k = date.today().isoformat()
        self.data["days"][k] = 3600
        self.data["cats"][k] = {"Coding": 3600}
        self.data["apps"][k] = {"code": 3600}
        self.data["cat_apps"][k] = {"Coding": {"code": 3600}}
        self.data["domains"][k] = {"Coding": {"github.com": 600}}
        self.data["titles"][k] = {"code - secret plan.txt": 60}
        offline.add_offline(k, "09:00", 30, "meeting", "Meetings", "")
        text = assistant.build_context()
        self.assertIn("total 1h 30m", text)
        self.assertIn("in person", text)
        self.assertIn("code 1h 00m", text)
        self.assertNotIn("github.com", text)
        self.assertNotIn("secret plan", text)
        self.data["config"]["ai_share_sites"] = True
        self.assertIn("github.com", assistant.build_context())

    def test_context_endpoint_shows_what_is_sent(self):
        text = self.jcall("GET", "/api/chat/context")[1]["text"]
        self.assertIn("Budget:", text)


if __name__ == "__main__":
    unittest.main()


class PromptTests(unittest.TestCase):
    def test_prompt_teaches_the_view_format_and_only_catalog_parts(self):
        from quota import assistant
        for word in ("a2ui", "surfaceUpdate", "beginRendering", "BarChart", "Progress", "Stat", "Table"):
            self.assertIn(word, assistant.SYSTEM_PROMPT)
