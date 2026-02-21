import os
import time
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import argparse

def crawl_facebook_marketplace_cli(city: str, query: str, max_price: int):
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

    city_id = cities.get(city, city.lower().replace(' ', '')) # Use .get with fallback for unsupported cities
    if city not in cities:
        print(f"Warning: '{city}' not found in predefined cities. Attempting to use '{city_id}' directly. This may fail if Facebook uses a different slug.", file=os.sys.stderr)


    marketplace_url = f'https://www.facebook.com/marketplace/{city_id}/search/?query={query}&maxPrice={max_price}'
    initial_url = "https://www.facebook.com/login/device-based/regular/login/"

    fb_email = os.getenv('FB_EMAIL')
    fb_password = os.getenv('FB_PASSWORD')

    if not fb_email or not fb_password:
        print("Error: FB_EMAIL and FB_PASSWORD environment variables must be set for login.", file=os.sys.stderr)
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Run headless
        page = browser.new_page()

        try:
            page.goto(initial_url)
            time.sleep(2) # Give page time to load login fields

            email_input_selector = 'input[name="email"]'
            password_input_selector = 'input[name="pass"]'

            # Check if login fields are present. If not, assume already logged in or direct access.
            if page.locator(email_input_selector).is_visible() and page.locator(password_input_selector).is_visible():
                page.fill(email_input_selector, fb_email)
                page.fill(password_input_selector, fb_password)
                time.sleep(2)
                login_button_locator = page.locator('div[role="button"]').filter(has_text="Log in")
                login_button_locator.click()
                time.sleep(40) # Increased sleep to allow for manual CAPTCHA solving and login processing
                # After solving CAPTCHA, you might need to manually click continue or Facebook will redirect
                time.sleep(5) # Additional sleep after manual interaction for redirects

                try:
                    # Wait for navigation to a typical logged-in URL, or for the login URL to disappear
                    page.wait_for_url(lambda url: not url.startswith(initial_url) and "login_error" not in url, timeout=30000)
                    print("Facebook login successful!", file=os.sys.stderr)
                except Exception as login_e:
                    print(f"Error: Facebook login failed or redirection took too long. Details: {login_e}", file=os.sys.stderr)
                    browser.close()
                    return []
            else:
                print("Login fields not found, assuming already logged in or direct marketplace access.", file=os.sys.stderr)


            page.goto(marketplace_url)
            time.sleep(5) # Increased sleep for marketplace page to load content

            # Optional: Scroll to load more content (if Facebook Marketplace uses infinite scroll)
            # for _ in range(3): # Scroll down 3 times
            #     page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            #     time.sleep(2)

        except Exception as e:
            print(f"An error occurred during navigation or login: {e}", file=os.sys.stderr)
            browser.close()
            return []

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        parsed = []

        # New CSS Selectors based on provided HTML snippet
        # These selectors are designed to be more robust than generic class names alone.

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
                # From the HTML: <span class="html-span ... " style="--x-WebkitLineClamp: 2;">Lenovo Golden Warrior A8 Unlocked 16GB</span>
                title_tag = listing.find('span', style=lambda s: s and '--x-WebkitLineClamp: 2;' in s)
                title = title_tag.text if title_tag else "N/A"

                # Location: <span> within a div/span structure, containing the location text.
                # Similar to title, it's nested and has a very long class list.
                # From the HTML: <span class="html-span ...">Richmond, BC</span>
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

    args = parser.parse_args()

    results = crawl_facebook_marketplace_cli(args.city, args.query, args.max_price)
    print(json.dumps(results, indent=2))
