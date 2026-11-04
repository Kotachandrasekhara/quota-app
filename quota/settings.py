"""Reading, checking and applying the settings."""
import re

from .status import _week_pct, compute_status
from .store import DATA, save


# ---------------------------------------------------------------- settings
def parse_kv_lines(text, label):
    rows = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{label}: write each line as 'Name: keyword, keyword'")
        name, rest = line.split(":", 1)
        rows.append((name.strip(), [k.strip().lower() for k in rest.split(",") if k.strip()]))
    return rows


def cats_to_text(categories):
    return "\n".join(f"{c['name']}: {', '.join(c.get('apps', []))}" for c in categories)


def titles_to_text(categories):
    return "\n".join(f"{c['name']}: {', '.join(c['titles'])}" for c in categories if c.get("titles"))


def text_fields(cfg):
    return {"categories_text": cats_to_text(cfg["categories"]), "titles_text": titles_to_text(cfg["categories"]),
            "browsers_text": ", ".join(cfg["browsers"])}


def validate_config(new):
    """Check settings coming from the Settings page; raise ValueError with a readable message."""
    cfg = {}

    def num(key, label, lo, hi, as_int=False, optional=False):
        v = new.get(key)
        if optional and (v is None or v == ""):
            cfg[key] = None
            return
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a number")
        if not lo <= v <= hi:
            raise ValueError(f"{label} must be between {lo} and {hi}")
        cfg[key] = int(v) if as_int else v

    num("daily_hours", "Daily hours", 0.5, 24)
    if "workdays" in new:
        try:
            wd = sorted({int(x) for x in new.get("workdays")})
        except (TypeError, ValueError):
            raise ValueError("Working days must be a list of weekdays")
        if not wd or any(x < 0 or x > 6 for x in wd):
            raise ValueError("Pick at least one working day")
        cfg["workdays"] = wd
    else:  # older callers send a count instead: Monday to that many days
        num("workdays_per_week", "Workdays per week", 1, 7, as_int=True)
        cfg["workdays"] = list(range(cfg["workdays_per_week"]))
    cfg["workdays_per_week"] = len(cfg["workdays"])
    num("weekly_hours", "Weekly hours", 1, 168, optional=True)
    if "private_remind_minutes" in new:
        num("private_remind_minutes", "Private mode reminder interval", 5, 480)
    num("idle_minutes", "Idle pause", 1, 120)
    num("remind_every_minutes", "Reminder interval", 5, 480)
    num("overtime_remind_minutes", "Overtime reminder interval", 1, 120)

    pcts = new.get("alert_percents", [])
    if isinstance(pcts, str):
        pcts = pcts.replace(",", " ").split()
    try:
        pcts = sorted({int(float(p)) for p in pcts})
    except (TypeError, ValueError):
        raise ValueError("Warning percentages must be numbers like 50, 75, 90, 100")
    if any(p < 1 or p > 200 for p in pcts):
        raise ValueError("Warning percentages must be between 1 and 200")
    cfg["alert_percents"] = pcts
    for key in ("track_categories", "classify_by_title", "track_apps", "track_titles", "track_domains"):
        cfg[key] = bool(new.get(key, DATA["config"].get(key, False)))

    if "categories_text" in new:
        cats, seen = [], set()
        for name, kws in parse_kv_lines(new.get("categories_text"), "Categories"):
            if not name or len(name) > 24 or "<" in name or ">" in name:
                raise ValueError("Category names must be 1 to 24 characters, without < or >")
            low = name.lower()
            if low == "other":
                raise ValueError("'Other' is reserved. It collects everything that matches no category")
            if low in seen:
                raise ValueError(f"Category '{name}' appears twice")
            if any(len(k) > 60 for k in kws):
                raise ValueError("Keywords must be 60 characters or fewer")
            seen.add(low)
            cats.append({"name": name, "apps": kws[:100], "titles": []})
        if not cats:
            raise ValueError("Add at least one category")
        if len(cats) > 6:
            raise ValueError("Use at most 6 categories")
        by_name = {c["name"].lower(): c for c in cats}
        for name, kws in parse_kv_lines(new.get("titles_text"), "Browser tab keywords"):
            target = by_name.get(name.lower())
            if not target:
                raise ValueError(f"Browser tab keywords: '{name}' is not in your category list")
            if any(len(k) > 60 for k in kws):
                raise ValueError("Keywords must be 60 characters or fewer")
            target["titles"] = kws[:100]
        cfg["categories"] = cats
        cfg["browsers"] = [b.strip().lower() for b in re.split(r"[,\n]", str(new.get("browsers_text", "")))
                           if b.strip()][:60]
    return cfg


def apply_config(cfg):
    """Apply validated settings immediately (caller holds the lock)."""
    DATA["config"].update(cfg)  # in place: the tracker thread sees changes right away
    status = compute_status()
    pct = _week_pct(status)
    fired = DATA["alerts"].get(status["week_start"], [])
    # if the limit was raised, thresholds that are no longer reached can fire again
    DATA["alerts"][status["week_start"]] = [a for a in fired if isinstance(a, str) or a <= pct]
    save(DATA)
