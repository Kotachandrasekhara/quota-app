"""History, rankings and CSV exports for the Dashboards page."""
import csv
import io
from datetime import date, timedelta

from .budget import away_secs, away_type, budgets, day_budget, off_type, week_budget, week_start
from .categories import cat_meta, category_names, classify, day_cat_apps, day_cats
from .config import OFF_TYPES
from .offline import offline_secs
from .store import DATA


def domain_tops(dates, n=10):
    """(top websites over all categories, {category: top websites})."""
    known = set(category_names())
    per = {}
    for k in dates:
        for cat, ds in DATA["domains"].get(k, {}).items():
            cat = cat if cat in known else "Other"
            b = per.setdefault(cat, {})
            for dom, v in ds.items():
                b[dom] = b.get(dom, 0) + v
    total, home = {}, {}
    for cat, b in per.items():
        for dom, v in b.items():
            total[dom] = total.get(dom, 0) + v
            if v > home.get(dom, (0, ""))[0]:
                home[dom] = (v, cat)
    rank = lambda t, cap: [{"name": a, "seconds": int(v)} for a, v in sorted(t.items(), key=lambda kv: -kv[1])[:cap]]
    overall = rank(total, max(n, 15))[:n if n < 15 else 15]
    for it in overall:
        it["cat"] = home[it["name"]][1]
    return overall, {c: rank(b, n) for c, b in per.items()}


def top_items(table, dates, n=10):
    agg = {}
    for d in dates:
        for k, v in table.get(d, {}).items():
            agg[k] = agg.get(k, 0) + v
    ranked = sorted(agg.items(), key=lambda kv: -kv[1])[:n]
    return [{"name": k, "seconds": int(v)} for k, v in ranked]


def top_apps(dates, n=15):
    items = top_items(DATA["apps"], dates, n)
    offline_cat = {e["label"]: e["cat"] for k in dates for e in DATA["offline"].get(k, [])}
    for it in items:  # logged time away from the computer carries the category it was logged under
        it["cat"] = offline_cat.get(it["name"]) or classify(it["name"], "")
    return items


def cat_top_apps(dates, n=10):
    known = set(category_names())
    agg = {}
    for k in dates:
        for cat, apps in day_cat_apps(k).items():
            cat = cat if cat in known else "Other"
            bucket = agg.setdefault(cat, {})
            for a, v in apps.items():
                bucket[a] = bucket.get(a, 0) + v
    return {c: [{"name": a, "seconds": int(v)} for a, v in sorted(b.items(), key=lambda kv: -kv[1])[:n]]
            for c, b in agg.items()}


# ---------------------------------------------------------------- history & reports
def parse_range(qs):
    today = date.today()
    try:
        end = date.fromisoformat(qs["to"][0]) if "to" in qs else today
        start = date.fromisoformat(qs["from"][0]) if "from" in qs else end - timedelta(days=29)
    except ValueError:
        raise ValueError("Dates must look like 2026-11-03")
    if start > end:
        raise ValueError("'from' must not be after 'to'")
    if (end - start).days > 366:
        raise ValueError("Range is limited to 367 days")
    return start, end


def sum_range(dates):
    used, cats = 0, {}
    for k in dates:
        used += int(DATA["days"].get(k, 0))
        for n, v in day_cats(k).items():
            cats[n] = cats.get(n, 0) + v
    return used, cats


def day_cat_hours(k):
    """({category: [seconds for each clock hour]}, estimated). Days recorded before per-category hours
    existed are split in proportion to that day's category mix, and flagged as estimated."""
    known = set(category_names())
    out, rec = {}, DATA["cat_hours"].get(k)
    if rec:
        for h, per in rec.items():
            for c, v in per.items():
                c = c if c in known else "Other"
                out.setdefault(c, [0] * 24)[int(h)] += v
        return out, False
    hours = DATA["hours"].get(k)
    cats = day_cats(k)
    total = sum(cats.values())
    if not hours or total <= 0:
        return out, False
    for c, cv in cats.items():
        row = out.setdefault(c, [0] * 24)
        for h, v in hours.items():
            row[int(h)] += v * cv / total
    return out, True


def history(start, end):
    daily_budget, weekly_budget = budgets()
    days, d = [], start
    while d <= end:
        k = d.isoformat()
        span = DATA["span"].get(k)
        days.append({"date": k, "weekday": d.weekday(), "used": int(DATA["days"].get(k, 0)),
                     "first": span[0] if span else None, "last": span[1] if span else None,
                     "cats": day_cats(k), "off": off_type(k), "away": away_secs(k), "away_type": away_type(k),
                     "offline": offline_secs(k), "budget": day_budget(k)})
        d += timedelta(days=1)
    weeks, w = [], week_start(start)
    while w <= end:  # whole Mon-Sun weeks that touch the range, so each compares to the weekly budget
        keys = [(w + timedelta(days=i)).isoformat() for i in range(7)]
        used, cats = sum_range(keys)
        weeks.append({"start": w.isoformat(), "used": used, "cats": cats, "budget": week_budget(w)})
        w += timedelta(days=7)
    keys = [x["date"] for x in days]
    hours = [0] * 24
    for k in keys:
        for h, v in DATA["hours"].get(k, {}).items():
            hours[int(h)] += int(v)
    cat_hours, estimated = {}, False
    for k in keys:
        per, est = day_cat_hours(k)
        estimated = estimated or est
        for c, row in per.items():
            agg = cat_hours.setdefault(c, [0] * 24)
            for h in range(24):
                agg[h] += row[h]
    cat_hours = {c: [int(round(v)) for v in row] for c, row in cat_hours.items()}
    span_days = (end - start).days + 1
    pstart, pend = start - timedelta(days=span_days), start - timedelta(days=1)
    pkeys = [(pstart + timedelta(days=i)).isoformat() for i in range(span_days)]
    pused, pcats = sum_range(pkeys)
    return {"from": start.isoformat(), "to": end.isoformat(),
            "daily_budget": daily_budget, "weekly_budget": weekly_budget,
            "categories": cat_meta(), "days": days, "weeks": weeks, "hours": hours,
            "cat_hours": cat_hours, "hours_estimated": estimated, "off_types": OFF_TYPES,
            "apps": top_apps(keys, 15), "cat_apps": cat_top_apps(keys),
            "domains": domain_tops(keys, 15)[0], "cat_domains": domain_tops(keys, 10)[1],
            "prior": {"from": pstart.isoformat(), "to": pend.isoformat(), "used": pused, "cats": pcats}}


def _safe_cell(v):
    v = str(v)  # stop spreadsheet apps from running app names / titles that look like formulas
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def export_csv(start, end, kind):
    daily_budget, _ = budgets()
    names = category_names() + ["Other"]
    out = io.StringIO()
    w = csv.writer(out)
    d = start
    if kind == "domains":
        w.writerow(["date", "website", "category", "seconds", "hours"])
        while d <= end:
            k = d.isoformat()
            for cat, ds in DATA["domains"].get(k, {}).items():
                for dom, sec in sorted(ds.items(), key=lambda kv: -kv[1]):
                    w.writerow([k, _safe_cell(dom), _safe_cell(cat), int(sec), round(sec / 3600, 2)])
            d += timedelta(days=1)
    elif kind == "apps":
        w.writerow(["date", "app", "category", "seconds", "hours"])
        while d <= end:
            k = d.isoformat()
            for app, sec in sorted(DATA["apps"].get(k, {}).items(), key=lambda kv: -kv[1]):
                w.writerow([k, _safe_cell(app), _safe_cell(classify(app, "")), int(sec), round(sec / 3600, 2)])
            d += timedelta(days=1)
    else:
        w.writerow(["date", "weekday", "day_type", "tokens_seconds", "hours"]
                   + [_safe_cell(f"{n} hours") for n in names]
                   + ["first_active", "last_active", "daily_budget_hours", "percent_of_daily_budget", "offline_hours"])
        while d <= end:
            k = d.isoformat()
            used = int(DATA["days"].get(k, 0))
            span = DATA["span"].get(k) or ["", ""]
            cats = day_cats(k)
            bud = day_budget(k)
            away = away_secs(k)
            note = OFF_TYPES.get(off_type(k), "") or (f"{OFF_TYPES[away_type(k)]} ({round(away / 3600, 2)}h)" if away else "")
            w.writerow([k, d.strftime("%a"), note, used, round(used / 3600, 2)]
                       + [round(cats.get(n, 0) / 3600, 2) for n in names]
                       + [span[0], span[1], round(bud / 3600, 2),
                          round(used / bud * 100, 1) if bud else "", round(offline_secs(k) / 3600, 2)])
            d += timedelta(days=1)
    return out.getvalue()
