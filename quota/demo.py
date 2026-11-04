"""Sample history for `python -m quota --demo`."""
from datetime import date, timedelta

from .categories import classify
from .config import MERGED_NAME
from .offline import add_offline
from .store import DATA, save


# ---------------------------------------------------------------- demo data
def seed_demo():
    import math
    import random
    rnd = random.Random(11)

    def hour_profile(cat, h):
        g = lambda centre, width: math.exp(-((h - centre) / width) ** 2)
        shape = {"Meetings": g(11, 1.4) + .8 * g(15, 1.4), "Coding": g(10, 2.2) + g(14.5, 2.2),
                 MERGED_NAME: g(13.5, 1.8) + g(8.5, 1.2) + g(16.5, 1.6),
                 "Other": g(12.5, 1.2) + .3 * g(9, 1)}
        return shape.get(cat, .3) + .03

    def split_hours(hours, cats):
        """Spread a day over clock hours and categories so both sets of totals match (iterative fitting)."""
        hs = sorted(int(h) for h in hours)
        names = [c for c in cats if cats[c] > 0]
        m = {(h, c): hour_profile(c, h) for h in hs for c in names}
        for _ in range(30):
            for h in hs:
                s = sum(m[(h, c)] for c in names) or 1
                for c in names:
                    m[(h, c)] *= hours[str(h)] / s
            for c in names:
                s = sum(m[(h, c)] for h in hs) or 1
                for h in hs:
                    m[(h, c)] *= cats[c] / s
        out = {str(h): {c: int(round(m[(h, c)])) for c in names if m[(h, c)] >= .5} for h in hs}
        return out, {h: sum(v.values()) for h, v in out.items()}
    mix = [("code", .34), ("terminal", .05), ("zoom.us", .12), ("teams", .05), ("chrome", .14),
           ("acrobat", .04), ("winword", .08), ("excel", .03), ("notion", .04), ("slack", .09),
           ("outlook", .04)]
    meet_mult = {0: .8, 1: 1.5, 2: 1.0, 3: 1.4, 4: .6}
    web_mix = [(MERGED_NAME, .66), ("Coding", .22), ("Meetings", .12)]
    SITES = {MERGED_NAME: [("docs.google.com", 4), ("notion.so", 3), ("news.ycombinator.com", 3), ("arxiv.org", 2),
                           ("en.wikipedia.org", 2), ("medium.com", 2), ("sharepoint.com", 2), ("overleaf.com", 1)],
             "Coding": [("github.com", 4), ("dev.azure.com", 3), ("portal.azure.com", 2), ("stackoverflow.com", 3),
                        ("developer.mozilla.org", 2), ("localhost", 1)],
             "Meetings": [("meet.google.com", 4), ("teams.microsoft.com", 2)]}
    today = date.today()
    for i in range(110):
        d = today - timedelta(days=109 - i)
        if d.weekday() >= 5 and rnd.random() < .9:
            continue
        if d != today and rnd.random() < .05:
            continue
        k = d.isoformat()
        target = 7.7 * 3600 * rnd.uniform(.6, 1.2) * (.85 if d.weekday() == 4 else 1)
        if d == today:
            target = 3.2 * 3600
        weights = {a: w * rnd.uniform(.6, 1.4) * (meet_mult.get(d.weekday(), 1) if a in ("zoom.us", "teams") else 1)
                   for a, w in mix}
        tot = sum(weights.values())
        apps = {a: int(target * w / tot) for a, w in weights.items()}
        DATA["apps"][k] = dict(apps)
        DATA["days"][k] = sum(apps.values())
        cats, cat_apps, doms = {}, {}, {}
        for a, sec in apps.items():
            if a == "chrome":  # the browser is split by what was on the tab, and by website
                left = sec
                for c, share in web_mix:
                    part = int(sec * share) if c != web_mix[-1][0] else left
                    left -= part
                    cats[c] = cats.get(c, 0) + part
                    cat_apps.setdefault(c, {})[a] = part
                    sites = SITES[c]
                    wts = [w * rnd.uniform(.5, 1.5) for _, w in sites]
                    rest = part
                    for j, ((dom, _), wt) in enumerate(zip(sites, wts)):
                        v = rest if j == len(sites) - 1 else int(part * wt / sum(wts))
                        rest -= v
                        if v > 0:
                            doms.setdefault(c, {})[dom] = v
                continue
            c = classify(a, "")
            cats[c] = cats.get(c, 0) + sec
            cat_apps.setdefault(c, {})[a] = sec
        DATA["cats"][k], DATA["cat_apps"][k], DATA["domains"][k] = cats, cat_apps, doms
        start = rnd.choice([8, 9, 9, 10])
        left, hr, hours = DATA["days"][k], start, {}
        while left > 0 and hr < 22:
            sec = min(left, int(rnd.uniform(1800, 3600)))
            hours[str(hr)] = sec
            left -= sec
            hr += 1
        DATA["cat_hours"][k], DATA["hours"][k] = split_hours(hours, cats)
        DATA["span"][k] = [f"{start:02d}:{rnd.randint(0, 40):02d}", f"{min(hr, 21):02d}:{rnd.randint(0, 59):02d}"]
    # a few days off, so leave and holidays have something to show
    def weekday_back(n):
        d = today - timedelta(days=n)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        return d

    leave_a = weekday_back(33)
    leave_b = leave_a - timedelta(days=1)
    while leave_b.weekday() >= 5:
        leave_b -= timedelta(days=1)
    plan = [(weekday_back(19), "holiday"), (leave_a, "leave"), (leave_b, "leave"), (weekday_back(9), "sick"),
            (today + timedelta(days=(4 - today.weekday()) % 7 or 7), "leave")]  # and one coming Friday
    for d, kind in plan:
        k = d.isoformat()
        DATA["off"][k] = kind
        for key in ("days", "apps", "cats", "cat_apps", "hours", "span", "cat_hours", "domains"):
            DATA[key].pop(k, None)
    for n, start, mins, kind, cat, note in [(2, "13:00", 90, "meeting", "Meetings", "Customer visit"),
                                            (12, "09:00", 240, "event", "Meetings", "Org all-hands"),
                                            (26, "14:00", 120, "training", MERGED_NAME, "Security training")]:
        k = weekday_back(n).isoformat()
        if k not in DATA["off"]:
            add_offline(k, start, mins, kind, cat, note)
    half = weekday_back(5)  # a morning of leave, so part-day leave has something to show
    DATA["part"][half.isoformat()] = {"type": "leave", "secs": int(3.5 * 3600)}
    save(DATA)
    print("Demo mode: loaded sample history. Your real data is not touched.")
