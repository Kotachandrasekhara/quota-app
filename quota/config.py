"""Constants, default settings and the two shared objects (lock, state)."""
import os
import sys
import threading


APP_NAME = "Quota"


DEMO = "--demo" in sys.argv or os.environ.get("QUOTA_DEMO") == "1"


HOME = os.path.expanduser("~")


APP_DIR = os.environ.get("QUOTA_DIR") or os.path.join(HOME, ".quota-demo" if DEMO else ".quota")


DATA_FILE = os.path.join(APP_DIR, "data.json")


OLD_DATA_FILE = os.path.join(HOME, ".tokentime", "data.json")  # earlier name of this app


PORT = 8765


SAMPLE_SECONDS = 5


# ---------------------------------------------------------------- default settings
DEFAULT_BROWSERS = ["chrome", "google chrome", "chromium", "msedge", "microsoft edge", "edge",
                    "firefox", "brave", "safari", "opera", "vivaldi", "orion", "librewolf"]


MERGED_NAME = "Reading & documenting"


OLD_NAMES = ("Reading", "Documenting")  # earlier versions had these as two categories


DEFAULT_CATEGORIES = [
    {"name": "Meetings",
     "apps": ["zoom", "teams", "ms-teams", "msteams", "microsoft teams", "webex", "cisco webex",
              "skype", "lync", "facetime", "gotomeeting", "bluejeans", "whereby"],
     "titles": ["google meet", "meet -", "meet –", "zoom meeting", "| microsoft teams",
                "teams meeting", "huddle", "webex"]},
    {"name": "Coding",
     "apps": ["code", "code - insiders", "visual studio code", "vscodium", "vscode", "cursor", "windsurf",
              "zed", "fleet", "intellij", "idea", "pycharm", "webstorm", "goland", "rider", "clion",
              "phpstorm", "rubymine", "datagrip", "jetbrains", "android studio", "studio64", "xcode",
              "eclipse", "netbeans", "monodevelop", "codeblocks", "qtcreator", "qt creator", "arduino",
              "spyder", "rstudio", "devenv", "visual studio", "ssms", "azuredatastudio", "azure data studio",
              "azure", "sublime", "atom", "notepad++", "vim", "nvim", "gvim", "emacs", "terminal", "iterm",
              "wezterm", "alacritty", "kitty", "warp", "windowsterminal", "powershell", "pwsh", "cmd",
              "conhost", "gnome-terminal", "konsole", "xterm", "git", "github desktop", "githubdesktop",
              "sourcetree", "postman", "insomnia", "docker", "dbeaver", "tableplus"],
     "titles": ["github", "gitlab", "bitbucket", "dev.azure.com", "azure devops", "portal.azure.com",
                "azure portal", "microsoft azure", "visualstudio.com", "stack overflow", "stackoverflow",
                "localhost", "127.0.0.1", "pull request", "jupyter", "colab", "codepen", "replit", "leetcode"]},
    {"name": MERGED_NAME,
     "apps": ["winword", "word", "microsoft word", "excel", "microsoft excel", "powerpnt", "powerpoint",
              "microsoft powerpoint", "onenote", "pages", "numbers", "keynote", "notion", "obsidian",
              "logseq", "typora", "bear", "notes", "evernote", "confluence", "soffice", "libreoffice",
              "wps", "onlyoffice", "textedit", "notepad", "gedit", "kate", "marktext", "scrivener",
              "ulysses", "acrobat", "acrord", "adobe reader", "foxit", "sumatra", "preview", "books",
              "kindle", "calibre", "evince", "okular", "zathura", "xreader", "atril", "skim", "zotero",
              "readwise", "reader", "pocket", "instapaper", "apple news", "mendeley"] + DEFAULT_BROWSERS,
     "titles": ["google docs", "google sheets", "google slides", "docs.google", "notion", "confluence",
                "sharepoint", "onenote", "word online", "overleaf"]},
]


DEFAULT_CONFIG = {
    "rules_version": 2,             # 2 = Reading and Documenting are one category; more IDEs and Azure under Coding
    "daily_hours": 7.7,             # length of your working day
    "workdays_per_week": 5,         # kept in sync with "workdays"
    "workdays": [0, 1, 2, 3, 4],    # the weekdays you work: 0 = Monday ... 6 = Sunday
    "weekly_hours": None,           # optional: set the weekly limit directly (overrides the line above)
    "idle_minutes": 5,              # no input for this long = not working (tokens pause)
    "remind_every_minutes": 60,     # gentle reminder while you are active
    "overtime_remind_minutes": 10,  # nag interval once tokens are used up
    "private_remind_minutes": 30,   # reminder while Private mode is on
    "alert_percents": [50, 75, 90, 100],
    "track_categories": True,       # sort your time into the categories below
    "classify_by_title": True,      # let browser tab titles decide the category (titles are not stored)
    "track_apps": True,             # record which app you are in (app name only)
    "track_titles": False,          # also store window titles (more detail, more private: off)
    "track_domains": True,          # record the website (domain only, never the page) while a browser is in front
    "categories": DEFAULT_CATEGORIES,
    "browsers": DEFAULT_BROWSERS,
}


lock = threading.Lock()


state = {"idle_seconds": 0.0, "active": False, "idle_supported": True, "now_app": None, "now_cat": None,
         "paused": False, "paused_at": None, "addr": None, "last_alert": None}  # Private mode is never saved: it is off every time Quota starts


OFFLINE_KINDS = {"meeting": "In-person meeting", "event": "Org event", "training": "Training",
                 "other": "Other work away from the computer"}


OFF_TYPES = {"holiday": "Holiday", "leave": "Leave", "sick": "Sick day"}
