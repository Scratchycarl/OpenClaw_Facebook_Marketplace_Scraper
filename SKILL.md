---
name: facebook-marketplace-scraper
description: Scrape Facebook Marketplace listings using Playwright and BeautifulSoup. Supports configurable searches by city, query, and maximum price. Requires a one-time login to save authentication state. Use when you need to extract structured data from Facebook Marketplace for research or personal use.
---

# Facebook Marketplace Scraper Skill

This skill allows you to search and extract listing information from Facebook Marketplace.

## Setup (One-time)

Before you can scrape, you need to log in to Facebook and save your authentication state. This generates an `auth_state.json` file that the scraper uses.

1.  **Run the login script:**
    ```bash
    python3 scripts/login_and_save_cookies.py
    ```
2.  A browser window will open. Log into Facebook manually.
3.  Once you are on the Facebook homepage, return to your terminal and **press Enter**.
4.  The script will save your login session to `facebook-scraper/auth_state.json`.

**Important:** The `facebook-scraper/.gitignore` file has been configured to prevent `auth_state.json` from being committed to your repository.

## Usage

Once authenticated, you can run the scraper with your desired search parameters:

```bash
python3 scripts/test.py --city "YOUR_CITY" --query "YOUR_SEARCH_QUERY" --max_price YOUR_MAX_PRICE [--no-headless]
```

### Arguments:

*   `--city` (required): The city for the search (e.g., "Richmond", "Vancouver").
*   `--query` (required): The search query (e.g., "iPad Air", "vintage bike").
*   `--max_price` (optional, default: 1000): Maximum price for listings.
*   `--no-headless` (optional): Use this flag to show the browser window during scraping (disable headless mode). By default, it runs silently in the background.

### Examples:

*   Search for "iPad Air" in "Richmond" with a max price of $500:
    ```bash
    python3 scripts/test.py --city "Richmond" --query "iPad Air" --max_price 500
    ```
*   Search for "Gaming PC" in "Burnaby" showing the browser window:
    ```bash
    python3 scripts/test.py --city "Burnaby" --query "Gaming PC" --no-headless
    ```

### Supported Cities:

The `test.py` script includes a predefined dictionary of cities, primarily focused on Metro Vancouver and surrounding areas in British Columbia. These cities use special Marketplace IDs for improved reliability. You can customize the `cities` dictionary within `scripts/test.py` to add or modify supported locations:

```python
cities = {
    'Vancouver': 'vancouver', 'Victoria': 'victoria', 'Burnaby': '110574778966847', 'Richmond': '112202378796934',
    'Surrey': '109571329060695', 'Kelowna': '111949595490847', 'Abbotsford': '112008808810771', 'Nanaimo': 'nanaimo',
    'Kamloops': '114995818516099', 'Prince George': '114995818516099', 'Coquitlam': '110019705694079',
    'Langley': '105471749485955', 'Delta': '106083456090237', 'Maple Ridge': '103746596331495', 'New Westminster': '115381681808519',
    'Courtenay': '103113716395848',
}
```

### Output Format:

The scraper prints a JSON array to standard output, where each dictionary represents a listing with the following fields: `name`, `price`, `location`, `image` (URL), and `link` (to the listing).

---
