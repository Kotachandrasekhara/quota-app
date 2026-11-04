import unittest
from datetime import date

from tests import support

from quota import budget


MON = date(2026, 11, 9)  # a Monday


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.data = support.reset()

    def test_default_week(self):
        self.assertEqual(budget.budgets(), (27720, 138600))  # 7.7 h, 38.5 h
        self.assertEqual(budget.week_budget(MON), 138600)

    def test_day_off_removes_one_day(self):
        budget.set_days_off(date(2026, 11, 10), date(2026, 11, 10), "leave", True)
        self.assertEqual(budget.week_budget(MON), 138600 - 27720)
        self.assertEqual(budget.day_budget("2026-11-10"), 0)

    def test_weekend_is_not_marked_when_workdays_only(self):
        self.assertEqual(budget.set_days_off(date(2026, 11, 14), date(2026, 11, 15), "holiday", True), 0)
        self.assertEqual(budget.set_days_off(date(2026, 11, 14), date(2026, 11, 15), "holiday", False), 2)
        self.assertEqual(budget.week_budget(MON), 138600)  # days you don't work cost nothing

    def test_part_day_leave(self):
        budget.set_days_off(date(2026, 11, 10), date(2026, 11, 10), "leave", True, away=2 * 3600)
        self.assertEqual(budget.day_budget("2026-11-10"), 27720 - 7200)
        self.assertEqual(budget.week_budget(MON), 138600 - 7200)

    def test_whole_day_replaces_part_day_and_none_clears(self):
        k = date(2026, 11, 10)
        budget.set_days_off(k, k, "leave", True, away=3600)
        budget.set_days_off(k, k, "holiday", True)
        self.assertNotIn("2026-11-10", self.data["part"])
        self.assertEqual(budget.off_type("2026-11-10"), "holiday")
        budget.set_days_off(k, k, None, True)
        self.assertEqual(budget.week_budget(MON), 138600)

    def test_weekly_hours_override_scales(self):
        self.data["config"]["weekly_hours"] = 30
        self.assertEqual(budget.budgets()[1], 108000)
        budget.set_days_off(date(2026, 11, 10), date(2026, 11, 10), "leave", True)
        self.assertEqual(budget.week_budget(MON), 108000 - 108000 // 5)

    def test_four_day_week(self):
        self.data["config"]["workdays"] = [0, 1, 2, 3]
        self.assertEqual(budget.budgets()[1], 27720 * 4)


if __name__ == "__main__":
    unittest.main()
