# Signup Automation – Authorized Partner Portal

## 🔗 Target Site
`https://authorized-partner.vercel.app/`

---

## 📋 Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.9+ |
| pip | Latest |
| OS | Windows / macOS / Linux |

---

## ⚙️ Setup & Installation

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <repo-folder>

# 2. (Optional but recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install playwright

# 4. Install Chromium browser driver
python -m playwright install chromium
```

---

## ▶️ Running the Script

```bash
python signup_automation_script.py
```

The script will:
1. Open the site homepage
2. Locate and click the Sign Up / Register link
3. Fill all form fields across every signup step automatically
4. Handle checkboxes (terms & conditions, consent)
5. Submit each page and detect the success state
6. Save screenshots at every step inside a `screenshots/` folder

---

## 🧪 Test Data Used

| Field | Value |
|---|---|
| First Name | Test |
| Last Name | User |
| Email | `testuser_<random>@mailinator.com` (randomised each run) |
| Password | `Test@1234!` |
| Phone | `+9779800000000` |
| Company | AutoTest Agency |
| Country | Nepal |
| City | Kathmandu |

> Emails use [Mailinator](https://www.mailinator.com/) — a free, disposable inbox — so no real account is needed. Check `https://www.mailinator.com/v4/public/inboxes.jsp?to=testuser_<generated-part>` for any verification emails.

---

## 📁 Project Structure

```
.
├── signup_automation_script.py   # Main automation script
├── README_execution_steps.md     # This file
├── test_report.pdf               # (generated after a run, optional)
└── screenshots/                  # Auto-created; one PNG per step
    ├── 00_homepage.png
    ├── 01_signup_page.png
    ├── step_1_before.png
    ├── step_1_after.png
    └── ...
```

---

## 🛠️ Framework & Versions

| Tool | Version |
|---|---|
| **Language** | Python 3.9+ |
| **Framework** | [Playwright for Python](https://playwright.dev/python/) |
| **Browser** | Chromium (installed via `playwright install chromium`) |
| **Playwright** | 1.40+ (`pip show playwright`) |

---

## 🔧 Customising Test Data

Open `signup_automation_script.py` and edit the `TEST_DATA` dictionary near the top:

```python
TEST_DATA = {
    "first_name": "Your Name",
    "email":      "your@email.com",
    ...
}
```

---

## 📌 Notes

- The script runs **headless** by default (no visible browser window).  
  To watch it run, change `headless=True` → `headless=False` in the script.
- Screenshots are saved automatically so you can review each step without watching the browser.
- The form-field selectors use broad patterns (`name`, `placeholder`, `id` matching) so the script adapts if field names change slightly.
