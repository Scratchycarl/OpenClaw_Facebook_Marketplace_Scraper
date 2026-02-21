import os
import time
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import argparse

def crawl_facebook_marketplace_cli(city: str, query: str, max_price: int, auth_state_path: str):
    # Dictionary of supported cities and their Facebook Marketplace IDs/slugs
    cities = {
        'New York': 'nyc', 'Los Angeles': 'la', 'Las Vegas': 'vegas', 'Chicago': 'chicago',
        'Houston': 'houston', 'San Antonio': 'sanantonio', 'Miami': 'miami', 'Orlando': 'orlando',
        'San Diego': 'sandiego', 'Arlington': 'arlington', 'Baltimore': 'baltimore',
        'Cincinnati': 'cincinnati', 'Denver': 'denver', 'Fort Worth': 'fortworth',
        'Jacksonville': 'jacksonville', 'Memphis': 'memphis', 'Nashville': 'nashville',
        'Philadelphia': 'philly', 'Portland': 'portland', 'San Jose': 'sanjose',
        'Tucson': 'tucson', 'Atlanta': 'atlanta', 'Boston': 'boston', 'Columbus': 'columbus',
        'Detroit': 'detroit', 'Honolulu': 'honolulu', 'Kansas City': 'kansascity',
        'New Orleans': 'neworleans', 'Phoenix': 'phoenix', 'Seattle': 'seattle',
        'Washington DC': 'dc', 'Milwaukee': 'milwaukee', 'Sacramento': 'sac',
        'Austin': 'austin', 'Charlotte': 'charlotte', 'Dallas': 'dallas', 'El Paso': 'elpaso',
        'Indianapolis': 'indianapolis', 'Louisville': 'louisville', 'Minneapolis': 'minneapolis',
        'Oklahoma City' : 'oklahoma', 'Pittsburgh': 'pittsburgh', 'San Francisco': 'sanfrancisco',
        'Tampa': 'tampa'
    }

    city_id = cities.get(city, city.lower().replace(' ', ''))
    if city not in cities:
        print(f"Warning: '{city}' not found in predefined cities. Attempting to use '{city_id}' directly. This may fail if Facebook uses a different slug.", file=os.sys.stderr)

    marketplace_url = f'https://www.facebook.com/marketplace/{city_id}/search/?query={query}&maxPrice={max_price}'

    if not os.path.exists(auth_state_path):
        print(f"Error: Authentication state file not found at {auth_state_path}. Please run login_and_save_cookies.py first.", file=os.sys.stderr)
        return []

    with sync_playwright() as p:
        # Load the saved authentication state
        browser = p.chromium.launch(headless=False) # Keep headless=False for debugging selectors
        context = browser.new_context(storage_state=auth_state_path)
        page = context.new_page()

        try:
            print(f"Navigating directly to marketplace URL: {marketplace_url}", file=os.sys.stderr)
            page.goto(marketplace_url, timeout=60000) # Increased timeout for navigation
            # Removed page.wait_for_load_state('networkidle') as it's too strict for dynamic pages.
            time.sleep(15) # Extended sleep to allow content to fully render after navigation

        except Exception as e:
            print(f"An error occurred during navigation: {e}", file=os.sys.stderr)
            browser.close()
            return []

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        parsed = []

        # New CSS Selectors based on your provided HTML snippet (February 20, 2026)
        # These selectors target unique attributes (like inline styles or specific combinations of classes)
        # to be more robust than generic class names.

        # Main listing container - targeting the div with specific style attributes for stability
        # From the HTML: <div class="..." style="max-width: 381px; min-width: 242px;">
        listings = soup.find_all('div', style=lambda s: s and 'max-width: 381px' in s and 'min-width: 242px' in s)

        for listing in listings:
            try:
                # Post URL: <a> tag with role="link" and href containing "/marketplace/item/"
                # From the HTML: <a class="..." href="/marketplace/item/..." role="link" tabindex="0">
                post_url_tag = listing.find('a', role='link', href=lambda href: href and '/marketplace/item/' in href)
                post_url = "https://www.facebook.com" + post_url_tag['href'] if post_url_tag and post_url_tag['href'].startswith('/') else post_url_tag['href'] if post_url_tag else None

                # Image: <img> tag with src containing "scontent" and common class
                # From the HTML: <img class="x15mokao ... xt7dq6l ..." src="https://scontent.fyvr2-1.fna.fbcdn.net/v/t45.5328-4/...">
                # Search within the post_url_tag's parent to ensure it's the correct image for this listing.
                image_tag = listing.find('img', class_=lambda c: c and 'xt7dq6l' in c, src=lambda s: s and 'scontent' in s)
                image = image_tag['src'] if image_tag else None

                # Price: <span> with specific inline style for font-size and line-height
                # From the HTML: <span dir="auto" class="xdmh292 ..." style="--x-fontSize: 17px; --x-lineHeight: 21.061px; ...">CA$5</span>
                price_tag = listing.find('span', dir='auto', style=lambda s: s and '--x-fontSize: 17px' in s)
                price = price_tag.text if price_tag else "N/A"

                # Title: <span> within a div/span structure, containing the main item name.
                # It's inside a larger span with specific classes, and often has a WebkitLineClamp style.
                # From the HTML: <span class="html-span ... " style="--x-WebkitLineClamp: 2;">GTRacing Gaming Chair</span>
                title_tag = listing.find('span', style=lambda s: s and '--x-WebkitLineClamp: 2;' in s)
                title = title_tag.text if title_tag else "N/A"

                # Location: <span> within a div/span structure, containing the location text.
                # Similar to title, it's nested and has a very long class list.
                # From the HTML: <span class="html-span ...">Los Angeles, CA</span>
                location_tag = listing.find('span', dir='auto', style=lambda s: s and '--x-fontSize: 13px' in s)
                location = location_tag.text if location_tag else "N/A"


                if all([image, title, price, post_url, location]):
                    parsed.append({
                        'name': title,
                        'price': price,
                        'location': location,
                        'image': image,
                        'link': post_url
                    })
            except Exception as e:
                # Log parsing errors to stderr to not interfere with JSON output
                print(f"Error parsing a listing: {e}", file=os.sys.stderr)
                pass # Continue to next listing even if one fails

        browser.close()
        return parsed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape Facebook Marketplace listings.')
    parser.add_argument('--city', required=True, help='City for the search (e.g., "Los Angeles").')
    parser.add_argument('--query', required=True, help='Search query (e.g., "vintage bike").')
    parser.add_argument('--max_price', type=int, default=1000, help='Maximum price for listings.')
    parser.add_argument('--auth_state_path', default="auth_state.json", help='Path to the authentication state file.')

    args = parser.parse_args()

    results = crawl_facebook_marketplace_cli(args.city, args.query, args.max_price, args.auth_state_path)
    print(json.dumps(results, indent=2))
