#!/usr/bin/env python3
import os
import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import argparse
from urllib.parse import quote_plus

# Regexes used for price extraction
CURRENCY_RE = re.compile(r'(?:CA\$|C\$|US\$|USD|\$)\s*[\d,]+(?:\.\d+)?', re.IGNORECASE)
FONT_RE = re.compile(r'--x-fontSize\s*:\s*([0-9.]+)px', re.IGNORECASE)

def extract_price_from_element(element, debug=False):
    """
    Robust extraction of the price from a listing container (BeautifulSoup element).
    Strategy:
      - look for <span> tags containing currency-like text
      - parse optional --x-fontSize from style and numeric value
      - prefer largest font-size if present, otherwise largest numeric value, otherwise first match
      - fallback: scan all visible text nodes in reading order and return first/last match
    """
    candidates = []

    for span in element.find_all('span'):
        txt = span.get_text(strip=True)
        if not txt:
            continue
        m = CURRENCY_RE.search(txt)
        if not m:
            continue
        text_val = m.group(0)
        # parse numeric part for heuristics
        try:
            num = float(re.sub(r'[^\d.]', '', text_val.replace(',', '')))
        except Exception:
            num = None

        style = span.get('style') or ''
        fs_m = FONT_RE.search(style)
        font_size = float(fs_m.group(1)) if fs_m else None

        candidates.append({'text': text_val, 'num': num, 'font_size': font_size, 'element': span})

    if debug:
        print("price candidates (spans):", candidates)

    if candidates:
        # prefer largest font-size present
        with_fs = [c for c in candidates if c['font_size'] is not None]
        if with_fs:
            best = max(with_fs, key=lambda c: c['font_size'])
            return best['text']
        # otherwise prefer largest numeric (usually asking price vs shipping)
        numeric = [c for c in candidates if c['num'] is not None]
        if numeric:
            best = max(numeric, key=lambda c: c['num'])
            return best['text']
        # fallback to first candidate
        return candidates[0]['text']

    # fallback: scan all visible texts in reading order
    texts = [t.strip() for t in element.stripped_strings if t.strip()]
    if debug:
        print("fallback all texts:", texts)
    # Usually price is near top — try first, then last
    for t in texts:
        m = CURRENCY_RE.search(t)
        if m:
            return m.group(0)
    # As final fallback, return "N/A"
    return "N/A"

def extract_title_and_location_from_texts(texts, price_text=None):
    """
    Given a list of texts (reading order), guess title and location.
    Heuristics:
      - If price_text is present, use its index as anchor: title likely follows, location after that.
      - Title: first fairly short non-price string that is not 'Sponsored' or similar.
      - Location: first string containing a comma and short length (e.g., "Richmond, BC" or "Los Angeles, CA")
    """
    title = "N/A"
    location = "N/A"

    # normalize texts
    clean_texts = [t for t in texts if t and t.lower() not in ('sponsored', 'ad')]

    # anchor on price if present
    if price_text:
        # find the text entry that contains the price_text
        for i, t in enumerate(clean_texts):
            if price_text in t:
                # title often next
                if i + 1 < len(clean_texts):
                    cand = clean_texts[i + 1]
                    # filter out obvious non-title tokens
                    if not CURRENCY_RE.search(cand) and len(cand) > 2 and ',' not in cand:
                        title = cand
                # location often after title
                if i + 2 < len(clean_texts):
                    cand2 = clean_texts[i + 2]
                    if ',' in cand2 and len(cand2) < 60:
                        location = cand2
                break

    # If still not found, pick first non-price, non-long text as title
    if title == "N/A":
        for t in clean_texts:
            if not CURRENCY_RE.search(t) and len(t) > 2 and len(t) < 120 and ',' not in t:
                title = t
                break

    # If still not found, find first text that looks like "City, ST" or has a comma
    if location == "N/A":
        for t in clean_texts:
            if ',' in t and len(t) < 60:
                location = t
                break

    return title, location

def find_card_container_from_anchor(a_tag):
    """
    Starting from the anchor that links to /marketplace/item/, climb parents to find a reasonable container
    that contains image or price/title text. We limit the climb to avoid selecting the whole page.
    """
    parent = a_tag
    for _ in range(6):  # climb up at most 6 levels
        parent = parent.parent
        if parent is None:
            break
        # heuristics: container that contains an <img> and some <span> text
        if parent.find('img') and parent.find('span'):
            return parent
    # fallback to the anchor's parent
    return a_tag.parent or a_tag

def crawl_facebook_marketplace_cli(city: str, query: str, max_price: int, auth_state_path: str, headless: bool = True, debug: bool = False):
    # Dictionary of supported cities and their Facebook Marketplace slugs
    cities = {
        'Vancouver': 'vancouver', 'Victoria': 'victoria', 'Burnaby': '110574778966847', 'Richmond': '112202378796934',
        'Surrey': '109571329060695', 'Kelowna': '111949595490847', 'Abbotsford': '112008808810771', 'Nanaimo': 'nanaimo',
        'Kamloops': '114995818516099', 'Prince George': '114995818516099', 'Coquitlam': '110019705694079',
        'Langley': '105471749485955', 'Delta': '106083456090237', 'Maple Ridge': '103746596331495', 'New Westminster': '115381681808519',
        'Courtenay': '103113716395848',
    }

    city_id = cities.get(city, city.lower().replace(' ', ''))
    if city not in cities:
        print(f"Warning: '{city}' not found in predefined cities. Attempting to use '{city_id}' directly. This may fail if Facebook uses a different slug.", file=os.sys.stderr)

    # URL-encode the query parameter
    encoded_query = quote_plus(query)
    marketplace_url = f'https://www.facebook.com/marketplace/{city_id}/search/?query={encoded_query}&maxPrice={max_price}'

    if not os.path.exists(auth_state_path):
        print(f"Error: Authentication state file not found at {auth_state_path}. Please run login_and_save_cookies.py first.", file=os.sys.stderr)
        return []

    with sync_playwright() as p:
        # Load the saved authentication state
        browser = p.chromium.launch(headless=headless)  # Change to True for headless operation
        context = browser.new_context(storage_state=auth_state_path)
        page = context.new_page()

        try:
            print(f"Navigating directly to marketplace URL: {marketplace_url}", file=os.sys.stderr)
            page.goto(marketplace_url, timeout=60000)
            # Give FB some time to load dynamic content and do a gentle scroll to trigger lazy loads
            time.sleep(4)
            # scroll down gradually to load more cards
            # for _ in range(6):
            #     page.evaluate("window.scrollBy(0, window.innerHeight);")
            #     time.sleep(1.2)
            # # allow extra time for hydration
            # time.sleep(6)

        except Exception as e:
            print(f"An error occurred during navigation: {e}", file=os.sys.stderr)
            browser.close()
            return []

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        parsed = []
        seen_urls = set()

        # Find all anchors that link to marketplace items (semantic)
        anchors = soup.find_all('a', href=lambda h: h and '/marketplace/item/' in h)
        if not anchors:
            # fallback: try to find cards by max-width style (older approach)
            anchors = []
            fallback_listings = soup.find_all('div', style=lambda s: s and 'max-width: 381px' in s and 'min-width: 242px' in s)
            for f in fallback_listings:
                a = f.find('a', href=lambda h: h and '/marketplace/item/' in h)
                if a:
                    anchors.append(a)

        for a in anchors:
            if debug:
                print(f"[DEBUG] Found raw Marketplace URL: {a.get('href')}", file=os.sys.stderr)
            try:
                href = a.get('href')
                if not href:
                    continue
                post_url = href if href.startswith('http') else "https://www.facebook.com" + href

                # dedupe
                if post_url in seen_urls:
                    continue
                seen_urls.add(post_url)

                # find a reasonable card/container for this anchor
                card = find_card_container_from_anchor(a)

                # image: choose first scontent img in the card
                img_tag = card.find('img', src=lambda s: s and 'scontent' in s)
                image = img_tag['src'] if img_tag else None

                # price
                price = extract_price_from_element(card)

                # build text list to guess title/location
                texts = [t.strip() for t in card.stripped_strings if t.strip()]

                title, location = extract_title_and_location_from_texts(texts, price_text=price)

                result = {
                    'name': title if title else "N/A",
                    'price': price if price else "N/A",
                    'location': location if location else "N/A",
                    'image': image,
                    'link': post_url
                }

                parsed.append(result)

            except Exception as e:
                print(f"Error parsing a listing: {e}", file=os.sys.stderr)
                continue

        browser.close()
        return parsed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape Facebook Marketplace listings.')
    parser.add_argument('--city', required=True, help='City for the search (e.g., "Los Angeles").')
    parser.add_argument('--query', required=True, help='Search query (e.g., "vintage bike").')
    parser.add_argument('--max_price', type=int, default=1000, help='Maximum price for listings.')
    parser.add_argument('--auth_state_path', default="auth_state.json", help='Path to the authentication state file.')
    parser.add_argument('--no-headless', action='store_false', dest='headless', default=True, help='Show browser window (disable headless mode)')
    parser.add_argument('--debug', action='store_true', help='Print all discovered Marketplace URLs for debugging.')
    args = parser.parse_args()

    results = crawl_facebook_marketplace_cli(args.city, args.query, args.max_price, args.auth_state_path, headless=args.headless, debug=args.debug)
    print(json.dumps(results, indent=2))
