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


if __name__ == "__main__":
    unittest.main()
