"""
signup_automation_script.py
Automates the full signup flow on https://authorized-partner.vercel.app/
Framework: Playwright (Python)
"""

import re
import time
import random
import string
from playwright.sync_api import sync_playwright, expect


# ─── Test Data ────────────────────────────────────────────────────────────────

def random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase, k=length))

def random_email():
    return f"testuser_{random_string()}@mailinator.com"

TEST_DATA = {
    "first_name":    "Test",
    "last_name":     "User",
    "email":         random_email(),
    "password":      "Test@1234!",
    "phone":         "+9779800000000",
    "company":       "AutoTest Agency",
    "country":       "Nepal",
    "city":          "Kathmandu",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def fill_if_visible(page, selector, value):
    """Fill a field only if it exists and is visible."""
    try:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            locator.first.fill(value)
            print(f"  ✔ Filled '{selector}' with '{value}'")
            return True
    except Exception as e:
        print(f"  ⚠ Could not fill '{selector}': {e}")
    return False


def click_if_visible(page, selector, description=""):
    """Click an element if it exists."""
    try:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            locator.first.click()
            print(f"  ✔ Clicked {description or selector}")
            return True
    except Exception as e:
        print(f"  ⚠ Could not click '{selector}': {e}")
    return False


def take_screenshot(page, name):
    path = f"screenshots/{name}.png"
    page.screenshot(path=path)
    print(f"  📸 Screenshot saved: {path}")


# ─── Page Handlers ────────────────────────────────────────────────────────────

def handle_signup_page(page):
    """
    Generic signup handler — covers multi-step forms.
    Tries common field selectors and submits each step.
    """
    step = 1
    while True:
        print(f"\n── Step {step} ──────────────────────────────")
        take_screenshot(page, f"step_{step}_before")

        # Personal info fields
        fill_if_visible(page, "input[name='firstName'], input[placeholder*='First'], input[id*='first']", TEST_DATA["first_name"])
        fill_if_visible(page, "input[name='lastName'],  input[placeholder*='Last'],  input[id*='last']",  TEST_DATA["last_name"])
        fill_if_visible(page, "input[type='email'],     input[name='email'],          input[id*='email']", TEST_DATA["email"])
        fill_if_visible(page, "input[type='password'],  input[name='password'],       input[id*='pass']",  TEST_DATA["password"])
        fill_if_visible(page, "input[name='confirmPassword'], input[placeholder*='Confirm']",              TEST_DATA["password"])
        fill_if_visible(page, "input[type='tel'],        input[name='phone'],          input[id*='phone']", TEST_DATA["phone"])
        fill_if_visible(page, "input[name='company'],    input[placeholder*='Company'],input[id*='company']",TEST_DATA["company"])
        fill_if_visible(page, "input[name='city'],       input[placeholder*='City'],   input[id*='city']",  TEST_DATA["city"])

        # Dropdowns
        for sel in ["select[name='country']", "select[id*='country']"]:
            try:
                el = page.locator(sel)
                if el.count() > 0 and el.first.is_visible():
                    el.first.select_option(label=TEST_DATA["country"])
                    print(f"  ✔ Selected country: {TEST_DATA['country']}")
            except Exception:
                pass

        # Checkboxes (terms / consent)
        for cb in page.locator("input[type='checkbox']").all():
            try:
                if not cb.is_checked():
                    cb.check()
                    print("  ✔ Checked a checkbox")
            except Exception:
                pass

        # Submit / Next button
        submitted = False
        for btn_text in ["Submit", "Next", "Continue", "Register", "Sign Up", "Create Account", "Get Started"]:
            btn = page.get_by_role("button", name=re.compile(btn_text, re.I))
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                print(f"  ✔ Clicked '{btn_text}' button")
                submitted = True
                break

        if not submitted:
            # Last resort: any submit-type button
            sub = page.locator("button[type='submit']")
            if sub.count() > 0 and sub.first.is_visible():
                sub.first.click()
                print("  ✔ Clicked submit button")
                submitted = True

        if not submitted:
            print("  ⚠ No submit button found — stopping.")
            break

        # Wait for navigation or next step
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            time.sleep(2)

        take_screenshot(page, f"step_{step}_after")

        # Detect success / end of flow
        url = page.url.lower()
        body = page.inner_text("body").lower()

        if any(kw in url for kw in ["dashboard", "welcome", "success", "thankyou", "thank-you", "home"]):
            print(f"\n✅ Signup completed! Redirected to: {page.url}")
            break

        if any(kw in body for kw in ["welcome", "thank you", "registration complete",
                                      "account created", "check your email",
                                      "verify your email", "successfully"]):
            print(f"\n✅ Signup completed! Success message detected.")
            break

        step += 1
        if step > 10:
            print("  ⚠ Exceeded max steps (10). Stopping.")
            break


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_signup_automation():
    import os
    os.makedirs("screenshots", exist_ok=True)

    base_url = "https://authorized-partner.vercel.app"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            print(f"\n🌐 Opening {base_url} …")
            page.goto(base_url, wait_until="networkidle", timeout=30000)
            take_screenshot(page, "00_homepage")

            # Find signup link
            signup_url = None
            for selector in [
                "a[href*='signup']",
                "a[href*='register']",
                "a[href*='sign-up']",
                "a:text-matches('sign up|register|get started|join', 'i')",
            ]:
                link = page.locator(selector)
                if link.count() > 0:
                    href = link.first.get_attribute("href") or ""
                    signup_url = href if href.startswith("http") else base_url + href
                    print(f"  ✔ Found signup link: {signup_url}")
                    link.first.click()
                    break

            if not signup_url:
                # Try button
                for btn_text in ["Sign Up", "Register", "Get Started", "Join"]:
                    btn = page.get_by_role("button", name=re.compile(btn_text, re.I))
                    if btn.count() > 0:
                        btn.first.click()
                        print(f"  ✔ Clicked '{btn_text}' button on homepage")
                        break

            page.wait_for_load_state("networkidle", timeout=15000)
            take_screenshot(page, "01_signup_page")
            print(f"  ➡ Signup page URL: {page.url}")

            handle_signup_page(page)

        except Exception as e:
            take_screenshot(page, "ERROR_state")
            print(f"\n❌ Error during automation: {e}")
            raise

        finally:
            context.close()
            browser.close()
            print("\n🏁 Browser closed.")


if __name__ == "__main__":
    run_signup_automation()
