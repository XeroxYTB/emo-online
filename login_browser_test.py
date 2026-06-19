"""One-off login page browser test for xeroxytb.com/login."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://xeroxytb.com/login"
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
OUT_DIR = Path(__file__).parent / "login_test_artifacts"
OUT_DIR.mkdir(exist_ok=True)


def ts():
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def main():
    report = {
        "started_at": ts(),
        "url": URL,
        "observations": [],
        "screenshots": [],
        "errors": [],
    }

    def log(msg):
        line = f"[{ts()}] {msg}"
        report["observations"].append(line)
        print(line, flush=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROME,
                headless=True,
                args=["--ignore-certificate-errors", "--no-sandbox"],
            )
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            log("Navigating to login page")
            page.goto(URL, wait_until="domcontentloaded", timeout=120000)

            boot_shot = OUT_DIR / "01_initial.png"
            page.screenshot(path=str(boot_shot), full_page=True)
            report["screenshots"].append(str(boot_shot))
            log(f"Screenshot saved: {boot_shot.name}")

            body_text = page.inner_text("body")[:2000]
            log(f"Initial body text snippet: {body_text[:300]!r}")

            has_boot_dots = page.locator(".login-boot-dots").count() > 0
            has_emo_eyes = page.locator(".emo-eyes, [class*='EmoEyes']").count() > 0
            log(f"Boot dots visible: {has_boot_dots}")
            log(f"Emo eyes visible: {has_emo_eyes}")

            google_btn = page.locator('[data-testid="google-login-btn"]')
            login_card = page.locator('[data-testid="login-card"]')
            retry_btn = page.get_by_role("button", name="Réessayer")

            deadline_ms = 90000
            poll_ms = 2000
            elapsed = 0
            final_state = "unknown"

            while elapsed <= deadline_ms:
                if google_btn.is_visible():
                    final_state = "google_ready"
                    break
                if login_card.is_visible() and google_btn.count() == 0:
                    final_state = "login_no_google"
                    break
                if retry_btn.is_visible():
                    final_state = "offline_retry"
                    break
                page.wait_for_timeout(poll_ms)
                elapsed += poll_ms
                if elapsed in (10000, 30000, 60000, 90000):
                    shot = OUT_DIR / f"wait_{elapsed//1000}s.png"
                    page.screenshot(path=str(shot), full_page=True)
                    report["screenshots"].append(str(shot))
                    msg = page.locator(".login-page p").first.inner_text() if page.locator(".login-page p").count() else ""
                    log(f"At {elapsed//1000}s — boot message: {msg!r}")

            final_shot = OUT_DIR / "02_final_state.png"
            page.screenshot(path=str(final_shot), full_page=True)
            report["screenshots"].append(str(final_shot))
            log(f"Final state after {elapsed//1000}s wait: {final_state}")

            toasts = page.locator("[data-sonner-toast], [role='status'], .toast")
            toast_count = toasts.count()
            toast_texts = []
            for i in range(min(toast_count, 5)):
                try:
                    toast_texts.append(toasts.nth(i).inner_text())
                except Exception:
                    pass
            log(f"Toast/error elements: {toast_count} — texts: {toast_texts}")

            scary = [t for t in toast_texts if t]
            if scary:
                log(f"Visible messages/toasts: {scary}")

            if google_btn.is_visible():
                log("Clicking Google login button")
                google_btn.click()
                page.wait_for_timeout(5000)
                click_shot = OUT_DIR / "03_after_google_click.png"
                page.screenshot(path=str(click_shot), full_page=True)
                report["screenshots"].append(str(click_shot))
                log(f"URL after click: {page.url}")
                log(f"Title after click: {page.title()}")
                after_text = page.inner_text("body")[:500]
                log(f"Body after click snippet: {after_text[:300]!r}")
            else:
                log("Google login button NOT visible — skip click test")

            browser.close()
    except Exception as e:
        report["errors"].append(str(e))
        log(f"ERROR: {e}")
        raise
    finally:
        report["finished_at"] = ts()
        report_path = OUT_DIR / "report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport written to {report_path}", flush=True)

    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
