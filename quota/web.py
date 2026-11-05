"""The dashboard's pages. The HTML, CSS and JavaScript live as plain files in quota/web."""
from pathlib import Path

WEB = Path(__file__).parent / "web"


def _read(name):
    return (WEB / name).read_text(encoding="utf-8")


def render_page(title, active, body, script):
    """Fill the page shell with a page's body and script."""
    css = _read("base.css").replace("/*DARK*/", _read("dark-tokens.css"))
    return (_read("shell.html").replace("%%TITLE%%", title).replace("%%ACTIVE%%", active).replace("%%CSS%%", css)
            .replace("%%BODY%%", body).replace("%%BASEJS%%", _read("base.js")).replace("%%SCRIPT%%", script))


def build_pages():
    pages = {
        "/": render_page("Quota: Today", "today", _read("pages/today.html"), _read("pages/today.js")),
        "/reports": render_page("Quota: Dashboards", "reports", _read("pages/reports.html"),
                                _read("pages/reports.js")),
        "/chat": render_page("Quota: Ask", "chat", _read("pages/chat.html"), _read("pages/chat.js")),
        "/settings": render_page("Quota: Settings", "settings", _read("pages/settings.html"),
                                 _read("pages/settings.js")),
    }
    pages["/history"] = pages["/reports"]  # the earlier address of the dashboards
    return pages


PAGES = build_pages()
