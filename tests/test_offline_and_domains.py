import unittest

from tests import support

from quota import offline, reports, system


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.data = support.reset()
        self.day = "2026-11-03"
        self.data["days"][self.day] = 1000
        self.data["cats"][self.day] = {"Coding": 1000}
        self.data["hours"][self.day] = {"10": 1000}

    def snapshot(self):
        return {k: repr(self.data[k]) for k in ("days", "cats", "hours", "apps", "cat_apps", "cat_hours")}

    def test_add_counts_as_work_and_remove_restores_everything(self):
        before = self.snapshot()
        e = offline.add_offline(self.day, "13:30", 90, "meeting", "Meetings", "Customer visit")
        self.assertEqual(self.data["days"][self.day], 1000 + 5400)
        self.assertEqual(self.data["cats"][self.day]["Meetings"], 5400)
        self.assertEqual(self.data["hours"][self.day]["13"], 1800)  # 13:30-14:00
        self.assertEqual(self.data["hours"][self.day]["14"], 3600)
        self.assertEqual(offline.offline_secs(self.day), 5400)
        self.assertTrue(offline.remove_offline(self.day, e["id"]))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(offline.remove_offline(self.day, e["id"]))

    def test_shows_in_top_apps_with_its_category(self):
        offline.add_offline(self.day, "09:00", 60, "event", "Meetings", "")
        apps = reports.top_apps([self.day])
        self.assertEqual(apps[0]["name"], "Org event")
        self.assertEqual(apps[0]["cat"], "Meetings")


class DomainTests(unittest.TestCase):
    def test_only_the_site_is_kept(self):
        cases = {
            "https://www.docs.google.com/a/b?c=1#d": "docs.google.com",
            "GitHub.com": "github.com",
            "localhost:3000": "localhost",
            "dev.azure.com/org/project/_boards": "dev.azure.com",
            "user@host.com": "host.com",
            "192.168.0.1": "192.168.0.1",
            "": "",
            "a b.com": "",
            "javascript:alert(1)": "",
            "x": "",
            "x" * 200 + ".com": "",
        }
        for raw, want in cases.items():
            self.assertEqual(system.clean_domain(raw), want, raw[:30])


if __name__ == "__main__":
    unittest.main()
