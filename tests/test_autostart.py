import os
import plistlib
import struct
import sys
import tempfile
import unittest
from unittest import mock

from tests import support

from quota import autostart, config
from quota.icon import png


class AutostartTests(unittest.TestCase):
    def setUp(self):
        support.reset()

    def test_launch_agent_starts_at_login_in_the_background(self):
        job = autostart.launch_agent()
        self.assertEqual(job["Label"], "com.quota.tracker")
        self.assertEqual(job["ProgramArguments"], [sys.executable, "-m", "quota", "--no-browser"])
        self.assertTrue(job["RunAtLoad"] and job["KeepAlive"])
        self.assertTrue(os.path.isdir(os.path.join(job["WorkingDirectory"], "quota")))
        plistlib.dumps(job)  # must be a valid property list

    def test_app_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "Quota.app")
            autostart.build_app(dest, make_icns=False)
            script = os.path.join(dest, "Contents", "MacOS", "Quota")
            self.assertTrue(os.access(script, os.X_OK))
            text = open(script).read()
            self.assertIn("http://127.0.0.1:%s" % config.PORT, text)
            self.assertIn("com.quota.tracker", text)
            with open(os.path.join(dest, "Contents", "Info.plist"), "rb") as f:
                info = plistlib.load(f)
            self.assertEqual(info["CFBundleExecutable"], "Quota")

    def test_paths_follow_the_home_folder(self):
        with mock.patch.dict(os.environ, {"HOME": "/Users/someone"}):
            self.assertEqual(autostart.plist_path(), "/Users/someone/Library/LaunchAgents/com.quota.tracker.plist")
            self.assertEqual(autostart.app_path(), "/Users/someone/Applications/Quota.app")

    def test_other_systems_get_instructions(self):
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(autostart.run("install"), 1)


class IconTests(unittest.TestCase):
    def test_png_is_valid_and_square(self):
        data = png(64)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (64, 64))


if __name__ == "__main__":
    unittest.main()
