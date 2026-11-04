"""Things that talk to the operating system: idle time, the front app, the front website, notifications."""
import json
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime

from .categories import is_browser, norm_app
from .config import state
from .store import DATA


BROWSER_APPS = {  # macOS browsers whose address Quota can read: name -> (application name, kind)
    "google chrome": ("Google Chrome", "chromium"), "chrome": ("Google Chrome", "chromium"),
    "microsoft edge": ("Microsoft Edge", "chromium"), "brave browser": ("Brave Browser", "chromium"),
    "chromium": ("Chromium", "chromium"), "vivaldi": ("Vivaldi", "chromium"), "arc": ("Arc", "chromium"),
    "opera": ("Opera", "chromium"), "safari": ("Safari", "safari")}


DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,98}[a-z0-9])?$")


# ---------------------------------------------------------------- idle detection
def idle_seconds():
    """Seconds since last keyboard/mouse input, or None if unsupported."""
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            info = LASTINPUTINFO()
            info.cbSize = ctypes.sizeof(info)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
            millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
            return millis / 1000.0
        if system == "Darwin":
            out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True,
                                 timeout=3).stdout
            for line in out.splitlines():
                if "HIDIdleTime" in line:
                    return int(line.split("=")[-1].strip()) / 1e9
            return None
        if shutil.which("xprintidle"):
            out = subprocess.run(["xprintidle"], capture_output=True, text=True, timeout=3).stdout
            return int(out.strip()) / 1000.0
        if shutil.which("gdbus"):
            out = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.gnome.Mutter.IdleMonitor",
                 "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
                 "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"],
                capture_output=True, text=True, timeout=3).stdout
            digits = "".join(c for c in out if c.isdigit())
            if digits:
                return int(digits) / 1000.0
    except Exception:
        return None
    return None


# ---------------------------------------------------------------- foreground app
def _title_wanted(name):
    cfg = DATA["config"]
    return bool(cfg.get("track_titles")
                or (cfg.get("track_categories") and cfg.get("classify_by_title") and is_browser(name)))


def active_app():
    """Return (app_name, window_title) of the foreground window, or (None, "")."""
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes
            from ctypes import wintypes
            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None, ""
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            name = None
            handle = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                    name = os.path.basename(buf.value)
                    if name.lower().endswith(".exe"):
                        name = name[:-4]
                kernel32.CloseHandle(handle)
            length = user32.GetWindowTextLengthW(hwnd)
            tbuf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, tbuf, length + 1)
            return name, tbuf.value
        if system == "Darwin":
            script = ('tell application "System Events" to get name of first '
                      'application process whose frontmost is true')
            name = subprocess.run(["osascript", "-e", script], capture_output=True, text=True,
                                  timeout=3).stdout.strip() or None
            title = ""
            if name and _title_wanted(name):
                # needs Accessibility permission for your terminal; silently empty otherwise
                t_script = ('tell application "System Events" to tell (first application process '
                            'whose frontmost is true) to get name of front window')
                title = subprocess.run(["osascript", "-e", t_script], capture_output=True, text=True,
                                       timeout=3).stdout.strip()
            return name, title
        if shutil.which("xdotool"):  # Linux / X11
            pid = subprocess.run(["xdotool", "getactivewindow", "getwindowpid"], capture_output=True,
                                 text=True, timeout=3).stdout.strip()
            title = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True,
                                   text=True, timeout=3).stdout.strip()
            name = None
            if pid.isdigit():
                with open(f"/proc/{pid}/comm", "r") as f:
                    name = f.read().strip()
            return name, title
    except Exception:
        pass
    return None, ""


def clean_domain(raw):
    """Just the website name from a URL or host: 'https://www.docs.google.com/a/b?c' -> 'docs.google.com'.
    The path, query and anything after it are dropped here, before anything is stored."""
    d = str(raw or "").strip().lower()
    if "//" in d:
        d = d.split("//", 1)[1]
    d = d.split("/")[0].split("?")[0].split("#")[0].split("@")[-1].split(":")[0]
    if d.startswith("www."):
        d = d[4:]
    if not DOMAIN_RE.match(d) or ("." not in d and d != "localhost"):
        return ""
    return d


def _windows_address(title):
    """Windows: read the address bar of the front browser window through the built-in UI Automation.
    Nothing to install. It can be blocked by company policy, and then no website is recorded."""
    cache = state["addr"]
    if cache and cache[0] == title and time.time() - cache[1] < 60:
        return cache[2]  # same window title as a moment ago: same page, skip the slow lookup
    import ctypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ps = ("Add-Type -AssemblyName UIAutomationClient;"
          "$r=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]%d);"
          "$c=New-Object System.Windows.Automation.PropertyCondition("
          "[System.Windows.Automation.AutomationElement]::ControlTypeProperty,"
          "[System.Windows.Automation.ControlType]::Edit);"
          "$e=$r.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$c);"
          "if($e){$e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value}" % int(hwnd))
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True,
                         text=True, timeout=8, creationflags=0x08000000).stdout
    dom = clean_domain(out.strip().splitlines()[0] if out.strip() else "")
    state["addr"] = (title, time.time(), dom)
    return dom


def browser_domain(app, title=""):
    """Website in front of the browser, as a domain (or ''). No extension needed: on a Mac Quota asks Chrome,
    Edge, Brave, Arc or Safari for the address of the front tab; on Windows it reads the address bar. Linux
    can't do this, so no websites are recorded there."""
    a = norm_app(app)
    system = platform.system()
    try:
        if system == "Windows":
            return _windows_address(title)
        if system == "Darwin" and a in BROWSER_APPS:
            name, kind = BROWSER_APPS[a]
            get = "URL of current tab of front window" if kind == "safari" else "URL of active tab of front window"
            lines = ['tell application "%s"' % name, "try", 'if (count of windows) is 0 then return ""',
                     'if mode of front window is "incognito" then return ""' if kind != "safari" else "",
                     "return " + get, "on error", 'return ""', "end try", "end tell"]
            cmd = ["osascript"]
            for ln in lines:
                if ln:
                    cmd += ["-e", ln]
            return clean_domain(subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout)
    except Exception:
        return ""
    return ""


# ---------------------------------------------------------------- notifications
def notify(title, message, live=None):
    print(f"[{datetime.now():%H:%M:%S}] {title}: {message}")
    state["last_alert"] = {"title": title, "message": message, "live": live, "ts": time.time(),
                           "time": datetime.now().strftime("%H:%M")}  # also shown on the Today page
    system = platform.system()
    try:
        if system == "Darwin":
            script = (f'display notification {json.dumps(message)} with title {json.dumps(title)} '
                      f'sound name "Glass"')
            subprocess.Popen(["osascript", "-e", script])
        elif system == "Windows":
            import ctypes
            threading.Thread(
                target=lambda: ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x40000),
                daemon=True).start()
        elif shutil.which("notify-send"):
            subprocess.Popen(["notify-send", "-u", "critical", title, message])
    except Exception:
        pass
