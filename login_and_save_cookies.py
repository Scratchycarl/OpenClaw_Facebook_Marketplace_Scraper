import os
import time
from playwright.sync_api import sync_playwright

def login_and_save_cookies(output_path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Keep headless=False for manual login
        page = browser.new_page()

        print("Navigating to Facebook login page. Please log in manually in the browser window that opens.", file=os.sys.stderr)
        page.goto("https://www.facebook.com") # Start with Facebook home or login
        
        # Give the user ample time to log in manually, solve CAPTCHA, etc.
        # This will block the script until the user presses Enter in the terminal
        input("Press Enter after you have successfully logged into Facebook in the browser window...")

        # Save the browser context (including cookies, local storage, etc.)
        # This includes authentication state
        context = page.context
        context.storage_state(path=output_path)
        print(f"Browser context saved to {output_path}", file=os.sys.stderr)

        browser.close()

if __name__ == "__main__":
    cookie_file = "auth_state.json"
    login_and_save_cookies(cookie_file)
    print(f"To use the saved session, set AUTH_STATE_PATH='{cookie_file}' in your environment for the scraping script.", file=os.sys.stderr)