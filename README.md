# Quota

Your week, metered in tokens. **1 token = 1 second of active computer time.**

Your weekly budget is daily hours x workdays (default 7.7 h x 5 = 38.5 h = **138,600 tokens**).
Tokens are spent only while you use the keyboard or mouse. When they run out, you stop.

Python 3.8+ and nothing else. Works on Windows, macOS and Linux. Everything stays on your computer.

## Run it

```
git clone <this repo>
cd quota-app
python -m quota
```

The app opens at http://127.0.0.1:8765. Keep the terminal open. To install a `quota` command instead:
`pip install .` and run `quota`.

**Demo for your team:** `python -m quota --demo` loads 110 days of sample history so every chart has data.
It uses its own folder (`~/.quota-demo`), so your real data is never touched.

- **Windows / macOS:** idle detection and app detection work out of the box
  (macOS asks once to allow "System Events").
- **Linux:** install `xprintidle` (idle) and `xdotool` (app names), on X11. Without them all running time is
  counted and apps show as "Unknown".

## What you get

- **Today:** a live token count that ticks down each second while you work, a bar for the week with one gap
  per day of budget, today by category, the week by day, and your top apps.
- **Dashboards:** an Overview and one dashboard each for **Meetings, Coding and Reading & documenting**.
  Each has totals, change versus the period before, daily and weekly charts, a calendar, weekday averages,
  top apps and a timesheet. Pick a preset range or custom dates.
- **Settings:** budget, reminders, what gets recorded, and your category rules. Changes apply immediately.
- **Reminders:** notifications at 50, 75, 90 and 100% of the week, when the day is done, hourly while you
  work, and every 10 minutes once tokens run out.
  They show as a pop-up from your computer and as a banner on the Today page. Settings has a "Send a test reminder" button to check they work on your machine.
- **Reports:** download days or apps as CSV, or print / save as PDF from the Dashboards page.
- **Days off and part-day leave:** use "Add leave or a day off" on the Today page, or Settings, Days off. Pick
  any date (past or coming up) and mark it Holiday, Leave or Sick day, for the whole day or for a few hours
  ("Part of the day", for example 2 hours for an appointment). A whole day off removes that day's share from the
  week's tokens; part-day leave removes the same share of a day, so 2 h away takes 2 h off the week. Days off show
  hatched on the charts and are left out of weekday averages; part-day leave lowers that day's budget line.
  Settings also lists them and can remove them, or mark a range of dates at once.
- **Time away from the computer:** for in-person meetings, org events and training, use "Log time away from the
  computer" on the Today page. Enter the date, start time, length and what it was, and pick the category it counts
  as (Meetings by default). It counts as work: it uses tokens, appears in that day's category, apps and time of
  day, and can be removed on Today or in Settings. Don't also log time you were at the computer.
- **Websites:** Quota records the **domain** of the site in front (for example `docs.google.com`), never the page,
  address or title. See "Top websites" on Today and on every dashboard (Reading & documenting too), and download
  them as CSV. The website also helps choose the category (a `github.com` tab counts as Coding). Nothing to
  install, no browser extension:
  - **Windows:** Quota reads the address bar of Chrome, Edge, Brave or Firefox through the built-in UI Automation
    (it runs a short PowerShell command). If your organisation blocks PowerShell, no websites are recorded and
    everything else still works.
  - **macOS:** Quota asks Chrome, Edge, Brave, Arc or Safari for the address of the front tab (macOS asks once to
    allow it). Safari private windows can't be told apart, so use Private mode for those.
  - **Linux:** not available.
  Turn it off in Settings, "What Quota records".
- **Private mode:** the switch in the top bar stops all recording (no time, apps or titles) until you turn it off.
  It is never saved, so it is **always off when Quota starts**. A banner shows while it is on, and Quota reminds
  you every 30 minutes (change in Settings).
- **Time of day:** hours by clock hour, split by category, on every dashboard, like Average by weekday.
  Days recorded before this version are split in proportion to their category totals.
- Light and dark themes (button in the top bar).

## How categories work

Each active second goes to the category of the app in front.

1. **Browsers:** the tab title decides first (a Google Meet tab is Meetings, a Google Docs tab is Reading & documenting,
   a GitHub, Azure DevOps or portal.azure.com tab is Coding). A browser tab that matches nothing counts as
   Reading & documenting.
2. **Other apps** match by name: VS Code and terminals are Coding, Zoom and Teams are Meetings, Word, Excel and
   Notion and PDF readers are Reading & documenting. All common IDEs count as Coding: Visual Studio Code,
   Visual Studio, the JetBrains IDEs, Xcode, Eclipse, Cursor and more.
3. Anything else is **Other**.

Edit the rules in **Settings, Categories**: one line per category, `Name: keyword, keyword`. An app matches when
its name starts with a keyword. You can have up to six categories (for example add `Chat: slack, outlook`).
History is sorted with the rules that applied when it was recorded. Days recorded before categories existed
are sorted by app name.

## Privacy

Everything stays in `~/.quota/data.json` on your computer. Nothing is sent anywhere, and the dashboard only
answers requests from your own machine. By default Quota stores app names and seconds. Browser tab titles are
read only to pick a category and are **not saved**. Turn on "Also save window titles" in Settings only if you
want titles kept. Turn off "Record which apps I use" to keep only category totals.

## Upgrading from TokenTime

The first run copies your history from `~/.tokentime/data.json`. Old days are sorted into categories by app name.

## Run it in the background and keep it in the Dock (macOS)

```
python -m quota install
```

This does two things:

1. **Starts Quota by itself every time you log in**, in the background, with no browser tab and no terminal.
   It is a standard macOS login job (`~/Library/LaunchAgents/com.quota.tracker.plist`) that restarts Quota if it
   ever stops. Log file: `~/Library/Logs/Quota.log`.
2. **Adds Quota.app to `~/Applications`**. Open it to start Quota if needed and show the dashboard in its own window
   (Chrome, Edge or Brave in app mode, otherwise your browser). Drag it to the Dock to keep it there.

Remove both with `python -m quota uninstall` (your data in `~/.quota` stays).

Notes:
- macOS may ask once to let Python control "System Events" (to see the front app) and to show notifications.
  Allow both. If reminders don't appear, check System Settings, Notifications.
- The install uses the Python you run it with. If you later move the project folder or change Python, run
  `python -m quota install` again.
- Prefer the dashboard to have its own Dock icon? Open http://127.0.0.1:8765 in Chrome, choose
  "Cast, save and share", then "Install page as app" (or Create shortcut, "Open as window"). In Safari 17 or newer,
  use File, "Add to Dock".
- Quota doesn't put an icon in the menu bar, since that needs an extra package. The Dock app and the browser tab are
  the way in.
- **Windows:** put a shortcut to `pythonw -m quota --no-browser` in `shell:startup`.
  **Linux:** add `python3 -m quota --no-browser` to your startup applications.

## Upgrading from the four-category version

On first start Quota merges your Reading and Documenting history and rules into **Reading & documenting**, adds the
newer Coding keywords (all IDEs, GitHub, Azure DevOps, Azure portal) to your Coding rules, and keeps a copy of your
data as `data.json.before-v2` in the Quota folder. Your own custom keywords are kept.

## Develop

```
python -m unittest discover -s tests -t .     # run the tests (no install needed)
python -m pyflakes quota tests                # lint (pip install pyflakes)
```

The code is split into small modules and the web page is plain HTML, CSS and JavaScript files.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a map, the data model and how to add things.
Environment variables for testing: `QUOTA_DIR` (use another data folder) and `QUOTA_DEMO=1`.
