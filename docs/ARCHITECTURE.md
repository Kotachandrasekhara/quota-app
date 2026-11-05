# How K(Qu)ota is put together

K(Qu)ota is a small Python program with no dependencies. One process does three jobs:

1. **Samples your activity** every 5 seconds (`tracker.py`), and writes it into the data.
2. **Serves a local web page** at `http://127.0.0.1:8765` (`server.py`) that shows the data.
3. **Reminds you** when you cross a limit (`alerts.py`, `system.notify`).

Everything is stored in one JSON file, `~/.quota/data.json`. Nothing leaves the computer.

## Modules (`quota/`)

| Module | What it does |
|---|---|
| `config.py` | Constants, default settings and categories, and two shared objects: `lock` and `state` (live values such as Private mode). |
| `store.py` | `DATA` (the in-memory copy of the file), `load`, `save`, and one-time upgrades of older files. |
| `categories.py` | `classify()` sorts an app, and for browsers the tab title and website, into a category. `day_cats()` reads a day's totals. |
| `system.py` | Everything that touches the operating system: idle time, front app, front website, notifications. One place to fix per platform. |
| `recording.py` | Adds one sample to the data (app, category, website, clock hour). |
| `offline.py` | Time away from the computer (in-person meetings, org events): added to and removed from the data. |
| `budget.py` | Daily and weekly budgets, days off, part-day leave. |
| `status.py` | The live snapshot behind the Today page. |
| `alerts.py` | The reminder rules. |
| `tracker.py` | The sampling loop (runs in a background thread). |
| `reports.py` | History, rankings and CSV export for the Dashboards page. |
| `assistant.py` | Ask K(Qu)ota: Azure OpenAI settings, the 30-day summary sent to the model, and the streaming call. |
| `settings.py` | Checks and applies the Settings form. |
| `demo.py` | Sample history for `python -m quota --demo`. |
| `autostart.py` | `python -m quota install`: the macOS login job (launchd) and KQuota.app for the Dock. |
| `icon.py` | Draws the app icon as a PNG (no image library). Served as `/icon.png` and used for KQuota.app. |
| `web.py` | Builds the pages from the files in `quota/web/`. |
| `server.py` | The HTTP handler (pages and `/api/...`) and `main()`. |

The dependency order is one-way: `config` <- `store` <- `categories` <- the rest. `server` sits on top.

## The web page (`quota/web/`)

Plain files, no build step: `shell.html` (frame), `base.css` and `dark-tokens.css`, `base.js` (shared charts and
helpers), and one `pages/<name>.html` + `.js` pair for Today, Dashboards (`reports`) and Settings. `web.py` joins
them into one HTML page per route when K(Qu)ota starts. Edit a file and restart K(Qu)ota to see the change.

## Data model (`data.json`)

`config` holds the settings. Every other key maps a day (`2026-11-04`) to numbers, in seconds:

| Key | Holds |
|---|---|
| `days` | Total active seconds. |
| `cats`, `cat_apps` | Seconds per category, and per app inside each category. |
| `apps`, `titles` | Seconds per app, and (only if you turn it on) per window title. |
| `hours`, `cat_hours` | Seconds per clock hour, and per hour and category. |
| `domains` | Seconds per website (domain only) inside each category. |
| `offline` | Logged time away from the computer. It is also counted in the keys above. |
| `off`, `part` | Days off, and part-day leave. These change budgets, not usage. |
| `span`, `alerts` | First and last active time of a day, and which reminders already fired this week. |

Private mode is never stored: it lives in `state` and is off every time K(Qu)ota starts.

## Security notes

- The server listens on `127.0.0.1` only, and answers only when the `Host` (and `Origin`, if sent) is the local
  dashboard. This blocks other websites and DNS rebinding.
- Every POST must be `application/json`, which a web page can't send to another origin without a preflight.
- App names, notes and websites are shown with `textContent` and escaped in CSV (a leading `=`, `+`, `-` or `@` is
  prefixed with `'`).
- The Azure key is stored in the data file (mode 600), never returned by any `/api` call, and only sent to the endpoint
  you entered (https, no redirects). Chat answers are shown as text, never as HTML.
- Only the website's domain is kept. The path, query and title are dropped before anything is stored.

## Adding things

- **A new platform feature** (for example, idle time on a new desktop): `system.py` only.
- **A new page**: add `pages/<name>.html` and `.js`, a route in `web.py`, and a link in `shell.html`.
- **A new data table**: add it to `TABLES` in `store.py`, then write to it in `recording.py`.
- Run `python -m unittest discover -s tests -t .` before you push.
