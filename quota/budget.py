"""Weekly and daily budgets, including days off and part-day leave."""
from datetime import timedelta

from .config import OFF_TYPES
from .store import DATA


# ---------------------------------------------------------------- budget maths
def week_start(d):
    return d - timedelta(days=d.weekday())  # Monday


def workday_set():
    return set(DATA["config"].get("workdays") or [0, 1, 2, 3, 4])


def budgets():
    """(daily, full weekly) budget in seconds from the current settings, before any days off."""
    cfg = DATA["config"]
    daily = int(round(cfg["daily_hours"] * 3600))
    if cfg.get("weekly_hours"):
        weekly = int(round(cfg["weekly_hours"] * 3600))
    else:
        weekly = daily * len(workday_set())
    return daily, weekly


def off_type(k):
    t = DATA["off"].get(k)
    return t if t in OFF_TYPES else None


def away_secs(k):
    """Seconds of part-day leave on day k (0 when the whole day is off or nothing is marked)."""
    if off_type(k):
        return 0
    p = DATA["part"].get(k)
    if not isinstance(p, dict) or p.get("type") not in OFF_TYPES:
        return 0
    return max(0, min(int(p.get("secs", 0)), 24 * 3600))


def away_type(k):
    p = DATA["part"].get(k)
    return p.get("type") if away_secs(k) and isinstance(p, dict) else None


def day_budget(k):
    """Budget for one day in seconds: 0 on a day off, reduced by any part-day leave."""
    if off_type(k):
        return 0
    daily = budgets()[0]
    return max(0, daily - away_secs(k))


def week_budget(monday):
    """Budget for the Mon-Sun week starting on `monday`. Each working day marked off removes its share."""
    _, full = budgets()
    wd = workday_set()
    daily = budgets()[0]
    share = full / len(wd)  # what one working day contributes to the week
    cut = 0.0
    for i in range(7):
        k = (monday + timedelta(days=i)).isoformat()
        if (monday + timedelta(days=i)).weekday() not in wd:
            continue
        if off_type(k):
            cut += share
        elif away_secs(k):
            cut += share * min(1.0, away_secs(k) / daily)
    return max(0, int(round(full - cut)))


def set_days_off(start, end, kind, workdays_only, away=None):
    """Mark every day from start to end as `kind` (None clears them). With `away` (seconds) only that much
    of each day is leave. Returns how many days changed."""
    wd, changed, d = workday_set(), 0, start
    while d <= end:
        k = d.isoformat()
        if kind is None:
            gone = DATA["off"].pop(k, None) is not None
            gone = DATA["part"].pop(k, None) is not None or gone
            changed += 1 if gone else 0
        elif (not workdays_only) or d.weekday() in wd:
            if away:
                want = {"type": kind, "secs": int(away)}
                if DATA["part"].get(k) != want or k in DATA["off"]:
                    DATA["part"][k] = want
                    DATA["off"].pop(k, None)
                    changed += 1
            elif DATA["off"].get(k) != kind or k in DATA["part"]:
                DATA["off"][k] = kind
                DATA["part"].pop(k, None)
                changed += 1
        d += timedelta(days=1)
    return changed
