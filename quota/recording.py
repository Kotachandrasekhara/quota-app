"""Writing samples into the data (apps, categories, websites, clock hours)."""
from datetime import datetime

from .store import DATA


def record_app(day, app, title, elapsed):
    app = app or "Unknown"
    apps = DATA["apps"].setdefault(day, {})
    apps[app] = apps.get(app, 0) + elapsed
    if DATA["config"].get("track_titles") and title:
        titles = DATA["titles"].setdefault(day, {})
        key = f"{app} - {title[:80]}"
        if key in titles or len(titles) < 300:
            titles[key] = titles.get(key, 0) + elapsed


def record_category(day, cat, app, elapsed):
    cats = DATA["cats"].setdefault(day, {})
    cats[cat] = cats.get(cat, 0) + elapsed
    if DATA["config"].get("track_apps"):
        per_app = DATA["cat_apps"].setdefault(day, {}).setdefault(cat, {})
        key = app or "Unknown"
        per_app[key] = per_app.get(key, 0) + elapsed


def record_domain(day, cat, domain, elapsed):
    per = DATA["domains"].setdefault(day, {}).setdefault(cat or "Other", {})
    if domain in per or len(per) < 200:
        per[domain] = per.get(domain, 0) + elapsed


def record_time_of_day(day, elapsed, cat=None):
    """Seconds per clock hour (and per category), plus first/last active time of the day."""
    now = datetime.now()
    hours = DATA["hours"].setdefault(day, {})
    hours[str(now.hour)] = hours.get(str(now.hour), 0) + elapsed
    if cat:
        row = DATA["cat_hours"].setdefault(day, {}).setdefault(str(now.hour), {})
        row[cat] = row.get(cat, 0) + elapsed
    stamp = now.strftime("%H:%M")
    span = DATA["span"].setdefault(day, [stamp, stamp])
    span[1] = stamp
