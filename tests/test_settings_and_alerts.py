import unittest
from datetime import date
from unittest import mock

from tests import support

from quota import alerts, budget, settings, status


def form(**over):
    base = {"daily_hours": "7.7", "workdays": [0, 1, 2, 3, 4], "weekly_hours": "", "idle_minutes": "5",
            "remind_every_minutes": "60", "overtime_remind_minutes": "10", "alert_percents": "50, 75, 90, 100"}
    base.update(over)
    return base


class SettingsTests(unittest.TestCase):
    def setUp(self):
        support.reset()

    def test_valid(self):
        cfg = settings.validate_config(form(weekly_hours="30", workdays=[0, 2]))
        self.assertEqual(cfg["weekly_hours"], 30)
        self.assertEqual(cfg["workdays"], [0, 2])
        self.assertEqual(cfg["alert_percents"], [50, 75, 90, 100])

    def test_errors_are_readable(self):
        for bad, text in [({"daily_hours": "abc"}, "Daily hours"), ({"daily_hours": "30"}, "between"),
                          ({"workdays": []}, "at least one"), ({"alert_percents": "x"}, "Warning percentages")]:
            with self.assertRaises(ValueError) as cm:
                settings.validate_config(form(**bad))
            self.assertIn(text, str(cm.exception))

    def test_category_rules(self):
        cfg = settings.validate_config(form(categories_text="Chat: slack, teams\nCoding: code",
                                            titles_text="Chat: huddle", browsers_text="chrome, edge"))
        self.assertEqual([c["name"] for c in cfg["categories"]], ["Chat", "Coding"])
        self.assertEqual(cfg["categories"][0]["titles"], ["huddle"])
        with self.assertRaises(ValueError):
            settings.validate_config(form(categories_text="Other: x"))
        with self.assertRaises(ValueError):
            settings.validate_config(form(categories_text="A: x\nB: x\nC: x\nD: x\nE: x\nF: x\nG: x"))


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.data = support.reset()
        self.today = date.today().isoformat()

    def fire(self):
        with mock.patch("quota.alerts.notify") as n:
            alerts.check_alerts(status.compute_status())
        return [c.args[0] for c in n.call_args_list]

    def test_each_threshold_fires_once(self):
        wk = budget.week_budget(budget.week_start(date.today()))
        self.data["days"][self.today] = wk * 0.52
        first = self.fire()
        self.assertIn("50% of weekly tokens used", first)
        self.assertNotIn("50% of weekly tokens used", self.fire())
        self.data["days"][self.today] = wk * 1.01
        self.assertIn("Weekly tokens used up", self.fire())

    def test_daily_reminder_respects_part_day_leave(self):
        budget.set_days_off(date.today(), date.today(), "leave", False, away=2 * 3600)
        self.data["days"][self.today] = 5.8 * 3600  # budget today is 5.7 h
        self.assertIn("Daily budget reached", self.fire())


if __name__ == "__main__":
    unittest.main()
