"""Reminders at percentages of the week and when the day is done."""
from datetime import date

from .config import OFF_TYPES
from .status import _week_pct, fmt
from .store import DATA
from .system import notify


def check_alerts(status):
    cfg = DATA["config"]
    wk = status["week_start"]
    fired = DATA["alerts"].setdefault(wk, [])
    pct = _week_pct(status)
    for threshold in cfg["alert_percents"]:
        if pct >= threshold and threshold not in fired:
            fired.append(threshold)
            if threshold >= 100:
                notify("Weekly tokens used up", "You have used your whole week. Time to stop.")
            else:
                notify(f"{threshold}% of weekly tokens used",
                       f"Left this week: {fmt(status['week_remaining'])}.", live="week_left")
    daily_key = f"daily-{date.today().isoformat()}"
    if status["today_off"]:
        if status["today_used"] > 0 and daily_key not in fired:
            fired.append(daily_key)
            notify("Today is a day off", f"You marked today as {OFF_TYPES[status['today_off']].lower()} "
                                         f"and have worked {fmt(status['today_used'])}.")
    elif status["today_used"] >= status["today_budget"] and daily_key not in fired:
        fired.append(daily_key)
        notify("Daily budget reached", f"You have worked {fmt(status['today_used'])} today.")
    for old in sorted(DATA["alerts"])[:-6]:  # keep only the last few weeks of alert history
        DATA["alerts"].pop(old, None)
