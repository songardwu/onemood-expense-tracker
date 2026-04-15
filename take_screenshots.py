"""
V5 UI Redesign — Before Screenshots
Takes screenshots of all 5 pages at desktop (1280px) and mobile (390px) viewports.
Saves to docs/screenshots/before/
"""
from playwright.sync_api import sync_playwright
import os

BASE = "http://127.0.0.1:5000"
OUT_DIR = "docs/screenshots/before"
os.makedirs(OUT_DIR, exist_ok=True)

# Pages to capture (path, name, requires_admin)
PAGES = [
    ("/login", "login", False),
    ("/", "list", True),
    ("/new", "new", True),
    ("/vendors", "vendors", True),
    ("/users", "users", True),  # admin only
]

VIEWPORTS = [
    ("desktop", 1280, 900),
    ("mobile", 390, 844),
]

def login(page, username="dawn", password="dawn1234"):
    """Log in and return authenticated page."""
    page.goto(f"{BASE}/login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for vp_name, width, height in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2,  # retina quality
            )
            page = context.new_page()

            logged_in = False

            for path, name, needs_auth in PAGES:
                if needs_auth and not logged_in:
                    login(page)
                    logged_in = True

                if path == "/login" and logged_in:
                    # Need a fresh context for login page (not logged in)
                    login_ctx = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=2,
                    )
                    login_page = login_ctx.new_page()
                    login_page.goto(f"{BASE}{path}")
                    login_page.wait_for_load_state("networkidle")
                    filename = f"{OUT_DIR}/{name}_{vp_name}.png"
                    login_page.screenshot(path=filename, full_page=True)
                    print(f"  OK  {filename}")
                    login_ctx.close()
                    continue

                page.goto(f"{BASE}{path}")
                page.wait_for_load_state("networkidle")
                # Small delay for any animations/renders
                page.wait_for_timeout(500)

                filename = f"{OUT_DIR}/{name}_{vp_name}.png"
                page.screenshot(path=filename, full_page=True)
                print(f"  OK  {filename}")

            context.close()

        browser.close()

    print(f"\nDone! {len(PAGES) * len(VIEWPORTS)} screenshots saved to {OUT_DIR}/")

if __name__ == "__main__":
    main()
