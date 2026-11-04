"""Start Quota when you log in (macOS), and a Quota.app you can keep in the Dock.

    python -m quota install      start at login, in the background, and add Quota.app to ~/Applications
    python -m quota uninstall    remove both
"""
import os
import plistlib
import shlex
import subprocess
import sys
import tempfile

from . import config
from .icon import png

LABEL = "com.quota.tracker"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the folder that holds the quota package


def _home():
    return os.path.expanduser("~")


def plist_path():
    return os.path.join(_home(), "Library", "LaunchAgents", LABEL + ".plist")


def app_path():
    return os.path.join(_home(), "Applications", "Quota.app")


def log_path():
    return os.path.join(_home(), "Library", "Logs", "Quota.log")


def launch_agent():
    """The launchd job: start at login, keep it running, no browser tab."""
    return {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, "-m", "quota", "--no-browser"],
        "WorkingDirectory": ROOT,
        "EnvironmentVariables": {"PYTHONPATH": ROOT},
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 30,  # if it can't start (for example the port is taken), wait before retrying
        "LimitLoadToSessionType": "Aqua",  # the desktop session: needed for notifications and app names
        "StandardOutPath": log_path(),
        "StandardErrorPath": log_path(),
    }


def launcher_script():
    """What Quota.app runs: make sure Quota is up, then open the dashboard in its own window."""
    q = shlex.quote
    return f"""#!/bin/bash
URL="http://127.0.0.1:{config.PORT}"
up() {{ curl -s -o /dev/null --max-time 1 "$URL/api/pause"; }}
if ! up; then
  launchctl kickstart -k "gui/$(id -u)/{LABEL}" >/dev/null 2>&1 || (cd {q(ROOT)} && PYTHONPATH={q(ROOT)} nohup {q(sys.executable)} -m quota --no-browser >>{q(log_path())} 2>&1 &)
  for i in $(seq 1 30); do up && break; sleep 0.5; done
fi
for B in "Google Chrome" "Microsoft Edge" "Brave Browser"; do
  if [ -d "/Applications/$B.app" ]; then open -na "$B" --args --app="$URL"; exit 0; fi
done
open "$URL"
"""


def build_app(dest, make_icns=True):
    """Create the Quota.app bundle at dest."""
    macos, res = os.path.join(dest, "Contents", "MacOS"), os.path.join(dest, "Contents", "Resources")
    os.makedirs(macos, exist_ok=True)
    os.makedirs(res, exist_ok=True)
    with open(os.path.join(dest, "Contents", "Info.plist"), "wb") as f:
        plistlib.dump({"CFBundleName": "Quota", "CFBundleDisplayName": "Quota", "CFBundleExecutable": "Quota",
                       "CFBundleIdentifier": "com.quota.launcher", "CFBundleIconFile": "Quota",
                       "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "1.0",
                       "LSMinimumSystemVersion": "10.13", "NSHighResolutionCapable": True}, f)
    script = os.path.join(macos, "Quota")
    with open(script, "w") as f:
        f.write(launcher_script())
    os.chmod(script, 0o755)
    if make_icns:
        try:
            _make_icns(os.path.join(res, "Quota.icns"))
        except Exception as e:  # the app works without an icon
            print("Could not make the icon:", e)


def _make_icns(target):
    names = {"icon_16x16.png": 16, "icon_16x16@2x.png": 32, "icon_32x32.png": 32, "icon_32x32@2x.png": 64,
             "icon_128x128.png": 128, "icon_128x128@2x.png": 256, "icon_256x256.png": 256,
             "icon_256x256@2x.png": 512, "icon_512x512.png": 512, "icon_512x512@2x.png": 1024}
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "Quota.iconset")
        os.makedirs(iconset)
        for name, size in names.items():
            with open(os.path.join(iconset, name), "wb") as f:
                f.write(png(size))
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", target], check=True, capture_output=True)


def _launchctl(*args):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def install():
    path = plist_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    os.makedirs(os.path.dirname(log_path()), exist_ok=True)
    with open(path, "wb") as f:
        plistlib.dump(launch_agent(), f)
    target = f"gui/{os.getuid()}"
    _launchctl("bootout", f"{target}/{LABEL}")  # replace an older copy, if any
    r = _launchctl("bootstrap", target, path)
    if r.returncode != 0:
        r = _launchctl("load", "-w", path)
    build_app(app_path())
    print("Quota will now start by itself when you log in.")
    print("  Background job:", path)
    print("  Log file:      ", log_path())
    print("  App:           ", app_path(), "(drag it to the Dock)")
    if r.returncode != 0:
        print("Could not start it right now:", (r.stderr or r.stdout).strip(), "- it will start at your next login.")
    else:
        print("It is running now: http://127.0.0.1:%s" % config.PORT)


def uninstall():
    path = plist_path()
    _launchctl("bootout", f"gui/{os.getuid()}/{LABEL}")
    for target in (path,):
        if os.path.exists(target):
            os.remove(target)
    app = app_path()
    if os.path.isdir(app):
        import shutil
        shutil.rmtree(app)
    print("Removed the login job and Quota.app. Your data in ~/.quota is untouched.")


def run(command):
    if sys.platform != "darwin":
        print("`python -m quota %s` is for macOS. On Windows, put a shortcut to `pythonw -m quota --no-browser` in "
              "shell:startup. On Linux, add `python3 -m quota --no-browser` to your startup applications." % command)
        return 1
    (install if command == "install" else uninstall)()
    return 0
