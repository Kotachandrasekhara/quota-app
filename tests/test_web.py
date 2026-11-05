import shutil
import subprocess
import tempfile
import unittest

from quota import web


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class JavaScriptTests(unittest.TestCase):
    def test_every_page_script_parses(self):
        for path, html in web.PAGES.items():
            scripts = html.split("<script>")[1:]
            for i, block in enumerate(scripts):
                code = block.split("</script>")[0]
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(code)
                r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{path} script {i}: {r.stderr}")


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class A2UITests(unittest.TestCase):
    def run_node(self, body):
        src = (web.WEB / "a2ui.js").read_text(encoding="utf-8")
        code = "const el=()=>({});\n" + src + "\n" + body
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_parses_wrapped_json_and_binds_data(self):
        out = self.run_node("""
const S=A2.parse('{"surfaceUpdate":{"surfaceId":"m","components":[\\n{"id":"root","component":{"Text":{"text":{"path":"/a"}}}}]}}\\n{"dataModelUpdate":{"surfaceId":"m","contents":{"a":"hi"}}}\\n{"beginRendering":{"surfaceId":"m","root":"root"}}');
console.log(JSON.stringify([Object.keys(S),S.m.root,S.m.data.a,Object.keys(S.m.comps)]));""")
        self.assertEqual(out, '[["m"],"root","hi",["root"]]')

    def test_split_and_strip(self):
        out = self.run_node("""
const t='Hello\\n```a2ui\\n{"beginRendering":{"root":"r"}}\\n```\\nBye\\n```a2ui\\n{"surf';
console.log(JSON.stringify(A2.split(t).map(p=>p.ui!=null?"ui":p.pending?"pending":"text")), JSON.stringify(A2.strip(t)));""")
        self.assertTrue(out.startswith('["text","ui","text","pending"]'))
        self.assertIn("[a chart or table was shown here]", out)


if __name__ == "__main__":
    unittest.main()
