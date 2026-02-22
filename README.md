# Facebook Marketplace Scraper (Playwright + BeautifulSoup)

A command-line Python tool that extracts listing data from Facebook Marketplace using a real authenticated browser session.

> ⚠️ **Warning**
> Using this software may violate Facebook’s Terms of Service and could result in temporary or permanent account restrictions.
> Use at your own risk.
> This project is intended for **personal research and educational purposes only**.

---

## Overview

This program logs into Facebook once, saves your session, and then performs Marketplace searches automatically.

It uses:

* **Playwright** → loads Marketplace pages like a real browser
* **BeautifulSoup** → parses rendered HTML
* **Heuristic extraction** → finds listing data despite Facebook’s constantly changing UI

Results are printed to the console in **JSON format**.

---

## Features

* 🔐 **Cookie-based authentication**
  Avoid repeated logins, CAPTCHAs, and 2FA prompts using a saved `auth_state.json`

* 🔎 **Configurable search**

  * City
  * Search query
  * Maximum price

* 🧠 **Robust extraction**
  Automatically extracts:

  * Title
  * Price
  * Location
  * Image URL
  * Listing link

* 🕶️ **Headless capable**
  Can run silently in the background after login

---

## Requirements

* Python 3.x
* playwright
* beautifulsoup4
* lxml
* Chromium (installed via Playwright)

---

## Installation

### 1. Clone repository

```bash
git clone https://github.com/Scratchycarl/OpenClaw_Facebook_Marketplace_Scraper
cd OpenClaw_Facebook_Marketplace_Scraper
```

### 2. Install dependencies

```bash
python3 -m pip install playwright beautifulsoup4 lxml
```

### 3. Install Playwright browser

```bash
python3 -m playwright install chromium
```

---

## Usage

## Step 1 — Login and Save Session (One-time setup)

You must create `auth_state.json` by logging in manually once.

Run:

```bash
python3 login_and_save_cookies.py
```

A browser will open:

1. Log into Facebook normally
2. Solve CAPTCHA / 2FA if prompted
3. Once on the homepage → return to terminal and press **Enter**

The script will save your login session as:

```
auth_state.json
```

---

## Step 2 — Run the Scraper

```bash
python3 main.py --city "" --query "" --max_price
```

### Example

```bash
python3 main.py --city "Richmond" --query "iPad Air" --max_price 100
```

---

## Supported Cities (Metro Vancouver, BC and surrounding areas)

The `main.py` script includes a predefined dictionary of cities, primarily focused on Metro Vancouver and surrounding areas in British Columbia. These cities use special Marketplace IDs for improved reliability. You can customize the `cities` dictionary within `main.py` to add or modify supported locations:

```python
cities = {
    'Vancouver': 'vancouver', 'Victoria': 'victoria', 'Burnaby': '110574778966847', 'Richmond': '112202378796934',
    'Surrey': '109571329060695', 'Kelowna': '111949595490847', 'Abbotsford': '112008808810771', 'Nanaimo': 'nanaimo',
    'Kamloops': '114995818516099', 'Prince George': '114995818516099', 'Coquitlam': '110019705694079',
    'Langley': '105471749485955', 'Delta': '106083456090237', 'Maple Ridge': '103746596331495', 'New Westminster': '115381681808519',
    'Courtenay': '103113716395848',
}
```

If your city isn’t listed, the script will attempt a generic slug and display a warning.

---

## Output Format

The scraper prints a JSON array:

```json
[
  {
    "name": "iPad Air 4 64GB",
    "price": "CA$100",
    "location": "Richmond, BC",
    "image": "https://scontent...",
    "link": "https://facebook.com/marketplace/item/123456"
  }
]
```

---

## Notes

* Facebook frequently changes HTML structure — occasional breakage is expected
* Do not run aggressively (high request frequency may trigger anti-bot detection)
* Use responsibly and ethically

