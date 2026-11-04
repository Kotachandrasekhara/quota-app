"""Sorting an app (and a browser tab) into a category, and reading a day's per-category totals."""
from .store import DATA


# ---------------------------------------------------------------- categories
def norm_app(name):
    n = (name or "").strip().lower()
    for suffix in (".exe", ".app"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return n


def is_browser(name):
    a = norm_app(name)
    return bool(a) and any(a.startswith(b) for b in DATA["config"].get("browsers", []))


def classify(app, title=""):
    """Category name for an app (and, for browsers only, the tab title). Everything else is 'Other'."""
    cfg = DATA["config"]
    a = norm_app(app)
    if not a:
        return "Other"
    if title and is_browser(a):
        t = title.lower()
        for c in cfg["categories"]:
            if any(k and k in t for k in c.get("titles", [])):
                return c["name"]
    for c in cfg["categories"]:
        if any(k and a.startswith(k) for k in c.get("apps", [])):
            return c["name"]
    return "Other"


def category_names():
    return [c["name"] for c in DATA["config"]["categories"]]


def cat_meta():
    meta = [{"name": n, "slot": i + 1} for i, n in enumerate(category_names())]
    meta.append({"name": "Other", "slot": 0})
    return meta


def day_cat_apps(k):
    """{category: {app: seconds}} for a day. Days recorded before categories existed are classified by app name."""
    rec = DATA["cat_apps"].get(k)
    if rec is not None:
        return rec
    out = {}
    for app, sec in DATA["apps"].get(k, {}).items():
        out.setdefault(classify(app, ""), {})[app] = sec
    return out


def day_cats(k):
    """{category: seconds} for a day. Time with no category (or an unknown one) is 'Other'; totals always add up."""
    used = float(DATA["days"].get(k, 0))
    rec = DATA["cats"].get(k)
    if rec is None:
        rec = {c: sum(apps.values()) for c, apps in day_cat_apps(k).items()}
    known = set(category_names())
    out = {}
    for name, v in rec.items():
        name = name if name in known else "Other"
        out[name] = out.get(name, 0) + float(v)
    total = sum(out.values())
    if total > used > 0:
        out = {n: v * used / total for n, v in out.items()}
    elif used > total:
        out["Other"] = out.get("Other", 0) + (used - total)
    return {n: int(round(v)) for n, v in out.items() if v >= 0.5}
