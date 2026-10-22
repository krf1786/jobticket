"""
Render a ticket URL to PDF with Playwright's Chromium.

Optional: if Playwright or its browser isn't installed, available() is False and
the app simply reports that snapshots are unavailable instead of failing.
"""
import threading, pathlib

BASE = pathlib.Path(__file__).resolve().parent
_lock = threading.Lock()          # one Chromium at a time; this box has other tenants


def available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        return False
    return True


def render(url: str, timeout_ms: int = 30000) -> bytes:
    from playwright.sync_api import sync_playwright
    with _lock, sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(400)          # let the save layer restore the form
            return page.pdf(format="Letter", print_background=True,
                            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        finally:
            browser.close()
