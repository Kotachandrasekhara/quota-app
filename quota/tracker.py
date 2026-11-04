"""The background loop that samples your activity every few seconds."""
import time
from datetime import date

from . import config
from .alerts import check_alerts
from .categories import classify, is_browser
from .config import APP_NAME, lock, state
from .recording import record_app, record_category, record_domain, record_time_of_day
from .status import compute_status, fmt
from .store import DATA, save
from .system import active_app, browser_domain, idle_seconds, notify


# ---------------------------------------------------------------- tracker loop
def tracker():
    last = time.time()
    last_save = time.time()
    last_reminder = time.time()
    last_overtime = 0.0
    last_private = time.time()
    cfg = DATA["config"]

    while True:
        time.sleep(config.SAMPLE_SECONDS)
        now = time.time()
        elapsed = min(now - last, config.SAMPLE_SECONDS * 4)  # ignore sleep/hibernate gaps
        last = now

        if state["paused"]:  # Private mode: look at nothing, record nothing
            state["active"] = False
            state["now_app"], state["now_cat"] = None, None
            last_reminder = now
            if now - last_private >= cfg["private_remind_minutes"] * 60:
                last_private = now
                notify("Private mode is on", "Nothing is being recorded. Turn it off when you are back at work.")
            continue
        last_private = now

        idle = idle_seconds()
        if idle is None:
            state["idle_supported"] = False
            idle = 0.0  # cannot detect: assume active
        state["idle_seconds"] = idle
        active = idle < cfg["idle_minutes"] * 60
        state["active"] = active

        if active:
            want_app = cfg.get("track_apps") or cfg.get("track_categories")
            app, title = active_app() if want_app else (None, "")
            domain = browser_domain(app, title) if app and cfg.get("track_domains") and is_browser(app) else ""
            hint = (title + " " + domain).strip() if cfg.get("classify_by_title") else title
            cat = classify(app, hint) if cfg.get("track_categories") else None
            if state["paused"]:  # Private mode was switched on while we were looking: drop this sample
                continue
            state["now_app"], state["now_cat"] = app, cat
            with lock:
                key = date.today().isoformat()
                DATA["days"][key] = DATA["days"].get(key, 0) + elapsed
                if cfg.get("track_apps"):
                    record_app(key, app, title, elapsed)
                if cat:
                    record_category(key, cat, app, elapsed)
                if domain:
                    record_domain(key, cat, domain, elapsed)
                record_time_of_day(key, elapsed, cat)
                status = compute_status()
            check_alerts(status)

            if now - last_reminder >= cfg["remind_every_minutes"] * 60:
                last_reminder = now
                if status["week_remaining"] > 0 and not status["today_off"]:
                    notify(APP_NAME,
                           f"Today {fmt(status['today_used'])} of {fmt(status['today_budget'])}. "
                           f"Left this week: {fmt(status['week_remaining'])}.")
            if status["week_remaining"] <= 0 and now - last_overtime >= cfg["overtime_remind_minutes"] * 60:
                last_overtime = now
                notify("Weekly tokens used up",
                       f"You are {fmt(-status['week_remaining'])} over your weekly budget. Time to stop.")
        else:
            state["now_app"], state["now_cat"] = None, None
            last_reminder = now  # the reminder timer only runs while you work

        if now - last_save >= 30:
            with lock:
                save(DATA)
            last_save = now
