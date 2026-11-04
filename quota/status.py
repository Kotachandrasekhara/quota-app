"""The live snapshot the Today page shows."""
from datetime import date, timedelta

from .budget import away_secs, away_type, budgets, day_budget, off_type, week_budget, week_start, workday_set
from .categories import cat_meta, day_cats
from .config import OFFLINE_KINDS, OFF_TYPES, state
from .offline import offline_view
from .reports import domain_tops, top_apps, top_items
from .store import DATA


def compute_status():
    today = date.today()
    start = week_start(today)
    daily_budget, _ = budgets()
    weekly_budget = week_budget(start)
    days, week_used, cats_week, week_off = [], 0, {}, 0
    for i in range(7):
        d = start + timedelta(days=i)
        k = d.isoformat()
        used = int(DATA["days"].get(k, 0))
        week_used += used
        if off_type(k):
            week_off += 1
        cats = day_cats(k)
        for n, v in cats.items():
            cats_week[n] = cats_week.get(n, 0) + v
        days.append({"date": k, "label": d.strftime("%a"), "used": used, "today": d == today, "cats": cats,
                     "off": off_type(k), "away": away_secs(k), "budget": day_budget(k)})
    today_key = today.isoformat()
    today_used = int(DATA["days"].get(today_key, 0))
    cfg = DATA["config"]
    return {
        "daily_budget": daily_budget, "weekly_budget": weekly_budget,
        "today_used": today_used, "week_used": week_used,
        "week_remaining": weekly_budget - week_used,  # negative = overtime
        "today_budget": day_budget(today_key), "today_off": off_type(today_key),
        "today_away": away_secs(today_key), "today_away_type": away_type(today_key),
        "last_alert": state["last_alert"], "domains_today": domain_tops([today_key], 8)[0], "offline_today": offline_view(today_key),
        "offline_kinds": OFFLINE_KINDS,
        "today_remaining": day_budget(today_key) - today_used,
        "off_types": OFF_TYPES, "paused": state["paused"],
        "days": days, "week_start": start.isoformat(), "week_off": week_off,
        "workdays": sorted(workday_set()),
        "active": state["active"], "idle_seconds": int(state["idle_seconds"]),
        "idle_supported": state["idle_supported"],
        "now": {"app": state["now_app"], "cat": state["now_cat"]},
        "categories": cat_meta(),
        "cats_today": day_cats(today_key), "cats_week": cats_week,
        "apps_today": top_apps([today_key], 8),
        "titles_today": top_items(DATA["titles"], [today_key]) if cfg.get("track_titles") else [],
    }


def fmt(seconds):
    sign = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    return f"{sign}{seconds // 3600}h {seconds % 3600 // 60:02d}m"


def _week_pct(status):
    """Share of the week's budget used. A week with no budget (every day off) counts as used up once you work."""
    if status["weekly_budget"] > 0:
        return status["week_used"] / status["weekly_budget"] * 100
    return 100 if status["week_used"] > 0 else 0
