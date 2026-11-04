import unittest

from tests import support

from quota import categories, config, store


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.data = support.reset()

    def test_ides_are_coding(self):
        for app in ("Code", "Visual Studio Code", "devenv", "idea64", "pycharm64", "rider64", "Xcode", "cursor"):
            self.assertEqual(categories.classify(app), "Coding", app)

    def test_azure_and_github_tabs_are_coding(self):
        for title in ("Boards - Azure DevOps - Microsoft Edge", "Home - Microsoft Azure", "dev.azure.com",
                      "pull request github.com", "portal.azure.com"):
            self.assertEqual(categories.classify("msedge", title), "Coding", title)

    def test_docs_and_unknown_tabs_are_reading_and_documenting(self):
        self.assertEqual(categories.classify("chrome", "Plan docs.google.com"), config.MERGED_NAME)
        self.assertEqual(categories.classify("chrome", "random page"), config.MERGED_NAME)
        self.assertEqual(categories.classify("winword"), config.MERGED_NAME)

    def test_meetings(self):
        self.assertEqual(categories.classify("Zoom.us"), "Meetings")
        self.assertEqual(categories.classify("chrome", "Standup - Google Meet"), "Meetings")

    def test_titles_only_count_in_browsers(self):
        self.assertEqual(categories.classify("slack", "github pull request"), "Other")

    def test_day_cats_add_up_to_the_day(self):
        self.data["days"]["2026-11-03"] = 1000
        self.data["cats"]["2026-11-03"] = {"Coding": 400, "Mystery": 100}  # unknown category folds into Other
        cats = categories.day_cats("2026-11-03")
        self.assertEqual(sum(cats.values()), 1000)
        self.assertEqual(cats["Other"], 600)


class MigrationTests(unittest.TestCase):
    def test_reading_and_documenting_are_merged(self):
        data = support.reset()
        data["config"]["categories"] = [
            {"name": "Coding", "apps": ["mycode"], "titles": []},
            {"name": "Documenting", "apps": ["word"], "titles": ["docs"]},
            {"name": "Reading", "apps": ["acrobat"], "titles": []},
        ]
        data["cats"]["2026-11-02"] = {"Documenting": 100, "Reading": 50, "Coding": 10}
        data["cat_apps"]["2026-11-02"] = {"Reading": {"chrome": 50}, "Documenting": {"chrome": 25, "word": 75}}
        data["cat_hours"]["2026-11-02"] = {"9": {"Reading": 5, "Documenting": 7}}
        data["domains"]["2026-11-02"] = {"Reading": {"a.com": 5}, "Documenting": {"a.com": 6}}
        data["offline"]["2026-11-02"] = [{"cat": "Reading"}]
        store.migrate_rules_v2(data)
        names = [c["name"] for c in data["config"]["categories"]]
        self.assertEqual(names, ["Coding", config.MERGED_NAME])
        merged = data["config"]["categories"][1]
        self.assertEqual(merged["apps"], ["word", "acrobat"])
        self.assertIn("mycode", data["config"]["categories"][0]["apps"])  # your own keyword is kept
        self.assertIn("dev.azure.com", data["config"]["categories"][0]["titles"])  # new Coding keyword added
        self.assertEqual(data["cats"]["2026-11-02"], {config.MERGED_NAME: 150, "Coding": 10})
        self.assertEqual(data["cat_apps"]["2026-11-02"][config.MERGED_NAME], {"chrome": 75, "word": 75})
        self.assertEqual(data["cat_hours"]["2026-11-02"]["9"], {config.MERGED_NAME: 12})
        self.assertEqual(data["domains"]["2026-11-02"][config.MERGED_NAME], {"a.com": 11})
        self.assertEqual(data["offline"]["2026-11-02"][0]["cat"], config.MERGED_NAME)
        self.assertEqual(data["config"]["rules_version"], 2)


if __name__ == "__main__":
    unittest.main()
