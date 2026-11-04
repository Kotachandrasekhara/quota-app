"""The data file: load, save, and the one-time upgrades of older files. DATA is the in-memory copy."""
import json
import os
import shutil

from .config import APP_DIR, DATA_FILE, DEFAULT_CATEGORIES, DEFAULT_CONFIG, DEMO, MERGED_NAME, OLD_DATA_FILE, OLD_NAMES


# Every table in the data file, besides "config". Each maps a day ("2026-11-04") or similar key to its numbers.
TABLES = ("days", "alerts", "apps", "titles", "hours", "span", "cats", "cat_apps", "off", "cat_hours", "part",
          "domains", "offline")

DATA = {}  # the in-memory copy of the data file; call init() once at start-up (and reset() in tests)


def fresh():
    """An empty data set with the default settings."""
    data = {"config": json.loads(json.dumps(DEFAULT_CONFIG))}
    for key in TABLES:
        data[key] = {}
    return data


def init():
    """Load the data file into DATA. Edits DATA in place, so other modules keep seeing the same object."""
    DATA.clear()
    DATA.update(load())


def reset():
    """Start from an empty data set (used by the tests)."""
    DATA.clear()
    DATA.update(fresh())


def load():
    os.makedirs(APP_DIR, exist_ok=True)
    if not DEMO and not os.path.exists(DATA_FILE) and os.path.exists(OLD_DATA_FILE):
        try:
            shutil.copyfile(OLD_DATA_FILE, DATA_FILE)
            print("Imported your history from", OLD_DATA_FILE)
        except Exception as e:
            print("Could not import old history:", e)
    data = fresh()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            cfg = loaded.get("config", {})
            if not isinstance(cfg.get("categories"), list) or not cfg.get("categories"):
                cfg.pop("categories", None)
            if not isinstance(cfg.get("browsers"), list):
                cfg.pop("browsers", None)
            data["config"].update(cfg)
            needs_v2 = int(cfg.get("rules_version", 1)) < 2
            if "workdays" not in cfg:  # settings saved before you could pick your working days
                n = max(1, min(7, int(data["config"].get("workdays_per_week") or 5)))
                data["config"]["workdays"] = list(range(n))
            for key in TABLES:
                data[key] = loaded.get(key, {})
            if needs_v2:
                try:
                    shutil.copyfile(DATA_FILE, DATA_FILE + ".before-v2")  # keep a copy of your history first
                    migrate_rules_v2(data)
                    print("Upgraded categories: Reading and Documenting are now one category.")
                except Exception as e:
                    print("Could not upgrade categories:", e)
        except Exception as e:
            print("Could not read data file, starting fresh:", e)
    return data


def _merge_into(dst, src):
    for k, v in src.items():
        if isinstance(v, dict):
            _merge_into(dst.setdefault(k, {}), v)
        else:
            dst[k] = dst.get(k, 0) + v


def _fold(d):
    """Move any 'Reading' / 'Documenting' entries of a dict into the merged category."""
    for old in OLD_NAMES:
        if old in d:
            v = d.pop(old)
            if isinstance(v, dict):
                _merge_into(d.setdefault(MERGED_NAME, {}), v)
            else:
                d[MERGED_NAME] = d.get(MERGED_NAME, 0) + v


def migrate_rules_v2(data):
    """One-time upgrade of saved settings and history: Reading + Documenting become one category, and the
    newer Coding keywords (all IDEs, GitHub, Azure DevOps, Azure portal) are added to your Coding rules."""
    cfg, cats = data["config"], data["config"].get("categories") or []
    old = [c for c in cats if c.get("name") in OLD_NAMES]
    if old:
        merged = {"name": MERGED_NAME, "apps": [], "titles": []}
        for c in old:
            for key in ("apps", "titles"):
                for kw in c.get(key, []):
                    if kw not in merged[key]:
                        merged[key].append(kw)
        pos = len([c for c in cats[:cats.index(old[0])] if c.get("name") not in OLD_NAMES])
        cats = [c for c in cats if c.get("name") not in OLD_NAMES]
        cats.insert(pos, merged)
    coding = next((c for c in cats if c.get("name") == "Coding"), None)
    if coding:
        for key in ("apps", "titles"):
            have = set(coding.get(key, []))
            coding[key] = list(coding.get(key, [])) + [k for k in DEFAULT_CATEGORIES[1][key] if k not in have]
    cfg["categories"] = cats
    cfg["rules_version"] = 2
    for table in ("cats", "cat_apps", "domains"):
        for rec in data[table].values():
            _fold(rec)
    for rec in data["cat_hours"].values():
        for per in rec.values():
            _fold(per)
    for entries in data["offline"].values():
        for e in entries:
            if e.get("cat") in OLD_NAMES:
                e["cat"] = MERGED_NAME


def save(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DATA_FILE)


