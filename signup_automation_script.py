

import os
import re
import sys
import time
import random
import string

from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Test Data
# ---------------------------------------------------------------------------

def _random_string(n=8):
    return "".join(random.choices(string.ascii_lowercase, k=n))

def _random_digits(n=8):
    return "".join(random.choices(string.digits, k=n))

_EMAIL_USER = f"testuser_{_random_string()}"

TEST_DATA = {
    "first_name":      "Test",
    "last_name":       "User",
    "email":           f"{_EMAIL_USER}@mailinator.com",
    "password":        "Test@1234!",
    # Nepal mobile: starts with 98, total 10 digits
    "phone":           "98" + _random_digits(8),
    "phone_country":   "+977",
    # Agency details
    "agency_name":     "AutoTest Agency",
    "agency_role":     "CEO",
    "agency_email":    f"agency_{_EMAIL_USER}@mailinator.com",
    "agency_website":  "autotestagency.com",
    "agency_address":  "Kathmandu, Nepal",
    "agency_region":   "Nepal",
    # Professional experience
    "years_experience": "5",
    "specialization":   "Real Estate",
    # Verification
    "country":         "Nepal",
    "city":            "Kathmandu",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg):
    """Print safely on Windows terminals (no Unicode crash)."""
    safe = str(msg).encode("ascii", errors="replace").decode("ascii")
    print(safe)


def ss(page, name):
    """Take and save a screenshot."""
    path = f"screenshots/{name}.png"
    try:
        page.screenshot(path=path, full_page=True)
        log(f"  [SS] {path}")
    except Exception as e:
        log(f"  [SS] Failed to save {path}: {e}")


def fill(page, selector, value, label=""):
    """Fill a visible input; silently skip if not found."""
    try:
        loc = page.locator(selector)
        if loc.count() > 0 and loc.first.is_visible():
            loc.first.fill(value)
            log(f"  [FILL] {label or selector} = {value}")
            return True
    except Exception as e:
        log(f"  [FILL] Error on {label or selector}: {e}")
    return False


def click_button(page, *texts):
    """Click the first visible button whose text matches any of *texts."""
    for text in texts:
        try:
            btn = page.locator("button", has_text=re.compile(text, re.I))
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                log(f"  [BTN] Clicked '{text}'")
                return True
        except Exception:
            pass
    return False


def click_submit(page):
    """Click button[type='submit'] as last resort."""
    try:
        sub = page.locator("button[type='submit']")
        if sub.count() > 0 and sub.first.is_visible():
            sub.first.click()
            log("  [BTN] Clicked submit button")
            return True
    except Exception:
        pass
    return False


def wait_stable(page, ms=6000):
    """Wait for network idle; fall back to sleep."""
    try:
        page.wait_for_load_state("networkidle", timeout=ms)
    except Exception:
        time.sleep(2)


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------

def step1_terms(page):
    """Step 1: Accept terms checkbox and click Continue."""
    log("\n[STEP 1] Terms & Conditions")
    ss(page, "01_terms")

    # The checkbox is a <button role='checkbox'> with id='remember'
    cb = page.locator("#remember")
    if cb.count() > 0 and cb.is_visible():
        state = cb.get_attribute("aria-checked") or cb.get_attribute("data-state")
        if state in ("false", "unchecked"):
            cb.click()
            log("  [CHECK] Terms checkbox checked")
        else:
            log("  [CHECK] Terms checkbox already checked")
    else:
        # Fallback: any checkbox
        for cb2 in page.locator("input[type='checkbox']").all():
            try:
                if not cb2.is_checked():
                    cb2.check()
            except Exception:
                pass

    time.sleep(0.5)

    # Click Continue (it's inside <a href=""><button>)
    clicked = click_button(page, "Continue")
    if not clicked:
        clicked = click_submit(page)
    if not clicked:
        log("  [WARN] No Continue button found on Step 1")

    wait_stable(page)
    ss(page, "01_terms_after")


def step2_account_setup(page):
    """Step 2: Personal details + phone (with country code) + password."""
    log("\n[STEP 2] Account Setup")
    ss(page, "02_account_setup")

    fill(page, "input[name='firstName']", TEST_DATA["first_name"], "First Name")
    fill(page, "input[name='lastName']",  TEST_DATA["last_name"],  "Last Name")
    fill(page, "input[name='email']",     TEST_DATA["email"],      "Email")

    # Phone country code (Radix combobox with role='combobox')
    try:
        combobox = page.locator("button[role='combobox']").first
        if combobox.is_visible():
            combobox.click()
            time.sleep(1)
            # Find option containing "+977"
            opt = page.locator("[role='option']").filter(has_text="+977").first
            if opt.count() > 0:
                opt.click()
                log("  [SELECT] Phone country code: +977")
            time.sleep(0.5)
    except Exception as e:
        log(f"  [WARN] Could not select phone country code: {e}")

    fill(page, "input[name='phoneNumber']",     TEST_DATA["phone"],    "Phone Number")
    fill(page, "input[name='password']",        TEST_DATA["password"], "Password")
    fill(page, "input[name='confirmPassword']", TEST_DATA["password"], "Confirm Password")

    ss(page, "02_account_filled")

    clicked = click_button(page, "Next") or click_submit(page)
    if not clicked:
        log("  [WARN] No Next button found on Step 2")

    # Wait for OTP input to appear
    try:
        page.wait_for_selector("input[data-input-otp='true']", timeout=15000)
        log("  [OK] OTP screen appeared")
    except Exception:
        log("  [WARN] OTP screen did not appear in time")

    ss(page, "02_account_after")


def step3_otp_verify(page, context):
    """Step 3: Fetch OTP from Mailinator and enter it."""
    log("\n[STEP 3] Email OTP Verification")
    ss(page, "03_otp_screen")

    email_user = _EMAIL_USER
    otp = _fetch_otp_from_mailinator(context, email_user)

    if not otp:
        log("  [ERROR] Could not retrieve OTP from Mailinator. Skipping OTP step.")
        ss(page, "03_otp_failed")
        return False

    log(f"  [OTP] Retrieved: {otp}")

    # Fill OTP (single input that accepts 6 digits)
    try:
        otp_input = page.locator("input[data-input-otp='true']")
        otp_input.fill(otp)
        log("  [FILL] OTP entered")
    except Exception as e:
        log(f"  [ERROR] Could not fill OTP: {e}")
        return False

    ss(page, "03_otp_filled")

    clicked = click_button(page, "Verify Code") or click_submit(page)
    if not clicked:
        log("  [WARN] No Verify Code button found")
        return False

    # Wait for next step
    try:
        page.wait_for_selector("input[name='agency_name']", timeout=15000)
        log("  [OK] Moved to Agency Details step")
    except Exception:
        log("  [WARN] Agency Details step did not appear in time")

    ss(page, "03_otp_after")
    return True


def _fetch_otp_from_mailinator(context, email_user):
    """Open Mailinator in a new page, read the OTP from the verification email."""
    mail_page = context.new_page()
    mail_url = f"https://www.mailinator.com/v4/public/inboxes.jsp?to={email_user}"
    try:
        log(f"  [MAIL] Opening: {mail_url}")
        mail_page.goto(mail_url, wait_until="networkidle", timeout=20000)

        # Wait for the email to arrive (up to 30s)
        try:
            mail_page.wait_for_selector(
                "tr:has-text('Signup Confirm OTP')", timeout=30000
            )
        except Exception:
            log("  [MAIL] Email did not arrive in 30s")
            mail_page.close()
            return None

        row = mail_page.locator("tr", has_text="Signup Confirm OTP")
        row.first.click()
        time.sleep(2)

        iframe = mail_page.frame_locator("#html_msg_body")
        body = iframe.locator("body").inner_text()
        match = re.search(r"\b(\d{6})\b", body)
        if match:
            otp = match.group(1)
            mail_page.close()
            return otp

        log("  [MAIL] 6-digit OTP not found in email body")
    except Exception as e:
        log(f"  [MAIL] Error reading Mailinator: {e}")
    finally:
        try:
            mail_page.close()
        except Exception:
            pass
    return None


def step4_agency_details(page):
    """Step 4: Agency Details."""
    log("\n[STEP 4] Agency Details")
    ss(page, "04_agency_details")

    fill(page, "input[name='agency_name']",    TEST_DATA["agency_name"],    "Agency Name")
    fill(page, "input[name='role_in_agency']", TEST_DATA["agency_role"],    "Role in Agency")
    fill(page, "input[name='agency_email']",   TEST_DATA["agency_email"],   "Agency Email")
    fill(page, "input[name='agency_website']", TEST_DATA["agency_website"], "Agency Website")
    fill(page, "input[name='agency_address']", TEST_DATA["agency_address"], "Agency Address")

    # Region of Operation (Radix multi-select combobox)
    try:
        region_combo = page.locator("button[role='combobox']").first
        if region_combo.is_visible():
            region_combo.click()
            time.sleep(1)
            # Select "Nepal" from dropdown list
            opt = page.get_by_text(TEST_DATA["agency_region"], exact=True)
            if opt.count() > 0 and opt.first.is_visible():
                opt.first.click()
                log(f"  [SELECT] Region: {TEST_DATA['agency_region']}")
            else:
                # Fallback: pick first visible option
                first_opt = page.locator("[role='option']").first
                if first_opt.count() > 0:
                    first_opt.click()
                    log("  [SELECT] Region: (first available option)")
            time.sleep(0.5)
            # Close dropdown by pressing Escape
            page.keyboard.press("Escape")
    except Exception as e:
        log(f"  [WARN] Could not select region: {e}")

    ss(page, "04_agency_filled")
    clicked = click_button(page, "Next") or click_submit(page)
    if not clicked:
        log("  [WARN] No Next button on Agency Details")

    wait_stable(page)
    ss(page, "04_agency_after")


def step5_professional_experience(page):
    """Step 5: Professional Experience — fill whatever fields appear."""
    log("\n[STEP 5] Professional Experience")
    ss(page, "05_experience")

    # Generic fill for any visible inputs
    inputs = page.locator("input:visible").all()
    for inp in inputs:
        name = inp.get_attribute("name") or ""
        placeholder = (inp.get_attribute("placeholder") or "").lower()
        itype = inp.get_attribute("type") or "text"

        if itype in ("submit", "hidden", "file", "checkbox", "radio"):
            continue

        if "year" in name.lower() or "year" in placeholder or "experience" in placeholder:
            inp.fill(TEST_DATA["years_experience"])
            log(f"  [FILL] {name or placeholder} = {TEST_DATA['years_experience']}")
        elif "special" in name.lower() or "special" in placeholder:
            inp.fill(TEST_DATA["specialization"])
            log(f"  [FILL] {name or placeholder} = {TEST_DATA['specialization']}")
        elif "city" in name.lower() or "city" in placeholder:
            inp.fill(TEST_DATA["city"])
            log(f"  [FILL] {name or placeholder} = {TEST_DATA['city']}")
        elif "country" in name.lower() or "country" in placeholder:
            inp.fill(TEST_DATA["country"])
            log(f"  [FILL] {name or placeholder} = {TEST_DATA['country']}")
        elif itype not in ("password",):
            # Fill generic text field with agency name as placeholder
            inp.fill(TEST_DATA["agency_name"])
            log(f"  [FILL] {name or placeholder} = (generic fill)")

    # Handle any visible <select> dropdowns
    for sel in page.locator("select:visible").all():
        try:
            options = sel.locator("option").all()
            if len(options) > 1:
                sel.select_option(index=1)
                log("  [SELECT] Dropdown: selected option index 1")
        except Exception:
            pass

    # Handle any visible Radix comboboxes
    for combo in page.locator("button[role='combobox']:visible").all():
        try:
            combo.click()
            time.sleep(0.5)
            first_opt = page.locator("[role='option']").first
            if first_opt.count() > 0:
                first_opt.click()
                log("  [SELECT] Radix combobox: first option selected")
            page.keyboard.press("Escape")
            time.sleep(0.3)
        except Exception:
            pass

    # Handle checkboxes
    for cb in page.locator("input[type='checkbox']:visible").all():
        try:
            if not cb.is_checked():
                cb.check()
                log("  [CHECK] Checkbox checked")
        except Exception:
            pass

    ss(page, "05_experience_filled")
    clicked = click_button(page, "Next", "Submit") or click_submit(page)
    if not clicked:
        log("  [WARN] No Next/Submit button on Professional Experience")

    wait_stable(page)
    ss(page, "05_experience_after")


def step6_verification_preferences(page):
    """Step 6: Verification & Preferences — fill whatever fields appear."""
    log("\n[STEP 6] Verification & Preferences")
    ss(page, "06_verification")

    # Generic fill for any visible inputs
    inputs = page.locator("input:visible").all()
    for inp in inputs:
        name = inp.get_attribute("name") or ""
        placeholder = (inp.get_attribute("placeholder") or "").lower()
        itype = inp.get_attribute("type") or "text"

        if itype in ("submit", "hidden", "file", "checkbox", "radio"):
            continue

        if "city" in name.lower() or "city" in placeholder:
            inp.fill(TEST_DATA["city"])
        elif "country" in name.lower() or "country" in placeholder:
            inp.fill(TEST_DATA["country"])
        elif itype not in ("password",):
            inp.fill(TEST_DATA["agency_name"])
            log(f"  [FILL] {name or placeholder} = (generic fill)")

    # Handle any Radix comboboxes
    for combo in page.locator("button[role='combobox']:visible").all():
        try:
            combo.click()
            time.sleep(0.5)
            first_opt = page.locator("[role='option']").first
            if first_opt.count() > 0:
                first_opt.click()
                log("  [SELECT] Radix combobox: first option selected")
            page.keyboard.press("Escape")
            time.sleep(0.3)
        except Exception:
            pass

    # Checkboxes
    for cb in page.locator("input[type='checkbox']:visible").all():
        try:
            if not cb.is_checked():
                cb.check()
                log("  [CHECK] Checkbox checked")
        except Exception:
            pass

    ss(page, "06_verification_filled")
    clicked = click_button(page, "Submit", "Finish", "Done", "Next") or click_submit(page)
    if not clicked:
        log("  [WARN] No Submit/Finish button on Verification step")

    wait_stable(page)
    ss(page, "06_verification_after")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_signup_automation():
    os.makedirs("screenshots", exist_ok=True)
    base_url = "https://authorized-partner.vercel.app"

    log("=" * 60)
    log("  Authorized Partner - Signup Automation")
    log("=" * 60)
    log(f"  Email  : {TEST_DATA['email']}")
    log(f"  Phone  : {TEST_DATA['phone_country']} {TEST_DATA['phone']}")
    log("=" * 60)

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
            # --- Homepage ---
            log(f"\n[NAV] Opening {base_url}")
            page.goto(base_url, wait_until="networkidle", timeout=30000)
            ss(page, "00_homepage")

            # Navigate to /register
            register_link = page.locator("a[href*='register']").first
            if register_link.count() > 0:
                register_link.click()
                log("[NAV] Clicked register link")
            else:
                page.goto(f"{base_url}/register", wait_until="networkidle", timeout=20000)
                log("[NAV] Navigated directly to /register")

            page.wait_for_load_state("networkidle", timeout=15000)
            ss(page, "00_register_landing")
            log(f"[NAV] Register URL: {page.url}")

            # --- Step 1: Terms ---
            page.wait_for_selector("#remember", timeout=10000)
            step1_terms(page)

            # --- Step 2: Account Setup ---
            page.wait_for_selector("input[name='firstName']", timeout=10000)
            step2_account_setup(page)

            # --- Step 3: OTP Verification ---
            otp_ok = step3_otp_verify(page, context)
            if not otp_ok:
                log("\n[ABORT] OTP verification failed. Automation cannot continue.")
                ss(page, "ABORT_otp_failure")
                return

            # --- Step 4: Agency Details ---
            step4_agency_details(page)

            # --- Steps 5+ : Generic handling for remaining steps ---
            for extra_step in range(5, 9):
                url = page.url
                log(f"\n[NAV] Current URL: {url}")

                if "experience" in url or "professional" in url:
                    step5_professional_experience(page)
                elif "verification" in url or "preference" in url:
                    step6_verification_preferences(page)
                else:
                    # Generic step handler
                    log(f"\n[STEP {extra_step}] Generic step handler")
                    ss(page, f"0{extra_step}_generic_step")

                    # Fill any visible inputs generically
                    inputs = page.locator("input:visible").all()
                    for inp in inputs:
                        itype = inp.get_attribute("type") or "text"
                        if itype in ("submit", "hidden", "file", "checkbox", "radio", "password"):
                            continue
                        inp.fill(TEST_DATA["agency_name"])

                    # Comboboxes
                    for combo in page.locator("button[role='combobox']:visible").all():
                        try:
                            combo.click()
                            time.sleep(0.5)
                            opt = page.locator("[role='option']").first
                            if opt.count() > 0:
                                opt.click()
                            page.keyboard.press("Escape")
                        except Exception:
                            pass

                    # Checkboxes
                    for cb in page.locator("input[type='checkbox']:visible").all():
                        try:
                            if not cb.is_checked():
                                cb.check()
                        except Exception:
                            pass

                    clicked = (
                        click_button(page, "Next", "Submit", "Finish", "Done", "Continue")
                        or click_submit(page)
                    )
                    wait_stable(page)
                    ss(page, f"0{extra_step}_generic_after")

                # Check for success
                current_url = page.url.lower()
                body_text = ""
                try:
                    body_text = page.inner_text("body").lower()
                except Exception:
                    pass

                success_urls = ["dashboard", "welcome", "success", "thankyou", "thank-you", "/home"]
                success_msgs = [
                    "registration complete", "account created",
                    "application submitted", "successfully registered",
                    "pending review", "under review", "submission received",
                ]

                if any(kw in current_url for kw in success_urls):
                    log(f"\n[SUCCESS] Signup complete! URL: {page.url}")
                    ss(page, "FINAL_success")
                    break

                if any(kw in body_text for kw in success_msgs):
                    log("\n[SUCCESS] Signup complete! Success message detected.")
                    ss(page, "FINAL_success")
                    break

                # If we are stuck on the same URL after the last extra step
                if extra_step == 8:
                    log("\n[INFO] Reached max generic steps. Taking final screenshot.")
                    ss(page, "FINAL_state")

        except Exception as exc:
            log(f"\n[ERROR] {exc}")
            try:
                ss(page, "ERROR_state")
            except Exception:
                pass
            raise

        finally:
            context.close()
            browser.close()
            log("\n[DONE] Browser closed.")
            log(f"       Screenshots saved in: screenshots/")


if __name__ == "__main__":
    run_signup_automation()
