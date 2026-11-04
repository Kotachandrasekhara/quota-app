"""Time away from the computer (in-person meetings, org events): added to and taken out of the data."""
import uuid

from .categories import day_cat_apps, day_cats
from .config import OFFLINE_KINDS
from .store import DATA


def _bump(table, day, keys, delta):
    """Add delta to table[day][keys...], creating levels on the way and pruning ones that end up empty."""
    path = [table.setdefault(day, {})]
    for k in keys[:-1]:
        path.append(path[-1].setdefault(k, {}))
    leaf = path[-1]
    leaf[keys[-1]] = max(0, leaf.get(keys[-1], 0) + delta)
    if leaf[keys[-1]] <= 0:
        leaf.pop(keys[-1])
    for depth in range(len(path) - 1, 0, -1):  # drop empty levels, deepest first
        if not path[depth]:
            path[depth - 1].pop(keys[depth - 1])
    if not path[0]:
        table.pop(day)


def apply_offline(day, e, sign):
    """Add (sign=1) or take back (sign=-1) a block of work away from the computer. It is counted like active time:
    it spends tokens, and shows under its category, its kind, and the clock hours it covered."""
    secs = int(e["mins"]) * 60 * sign
    if day not in DATA["cats"]:
        DATA["cats"][day] = dict(day_cats(day))  # keep the estimate for days recorded before categories existed
    if day not in DATA["cat_apps"]:
        DATA["cat_apps"][day] = {c: dict(v) for c, v in day_cat_apps(day).items()}
    DATA["days"][day] = max(0, DATA["days"].get(day, 0) + secs)
    if not DATA["days"][day]:
        DATA["days"].pop(day)
    _bump(DATA["cats"], day, [e["cat"]], secs)
    if e.get("apps"):
        _bump(DATA["apps"], day, [e["label"]], secs)
        _bump(DATA["cat_apps"], day, [e["cat"], e["label"]], secs)
    for h, v in e["hours"].items():
        _bump(DATA["hours"], day, [h], v * sign)
        _bump(DATA["cat_hours"], day, [h, e["cat"]], v * sign)
    if sign > 0:
        end = e["start"].split(":")
        t_end = int(end[0]) * 60 + int(end[1]) + int(e["mins"])
        span = DATA["span"].setdefault(day, [e["start"], e["start"]])
        span[0] = min(span[0], e["start"])
        span[1] = max(span[1], f"{min(t_end, 1439) // 60:02d}:{min(t_end, 1439) % 60:02d}")


def offline_secs(k):
    return sum(int(e.get("mins", 0)) * 60 for e in DATA["offline"].get(k, []))


def offline_view(k):
    return [{"id": e["id"], "start": e["start"], "mins": e["mins"], "kind": e["label"], "cat": e["cat"],
             "note": e.get("note", "")} for e in DATA["offline"].get(k, [])]


def add_offline(day, start, mins, kind, cat, note):
    hours, t, left = {}, int(start[:2]) * 60 + int(start[3:]), mins
    while left > 0:
        chunk = min(left, (t // 60 + 1) * 60 - t)
        hours[str(t // 60)] = hours.get(str(t // 60), 0) + chunk * 60
        t, left = t + chunk, left - chunk
    e = {"id": uuid.uuid4().hex[:8], "start": start, "mins": mins, "kind": kind, "label": OFFLINE_KINDS[kind],
         "cat": cat, "note": note, "hours": hours, "apps": bool(DATA["config"].get("track_apps"))}
    DATA["offline"].setdefault(day, []).append(e)
    apply_offline(day, e, 1)
    return e


def remove_offline(day, eid):
    items = DATA["offline"].get(day, [])
    for e in items:
        if e["id"] == eid:
            apply_offline(day, e, -1)
            items.remove(e)
            if not items:
                DATA["offline"].pop(day, None)
            return True
    return False
