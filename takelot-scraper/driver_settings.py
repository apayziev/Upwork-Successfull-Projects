from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent


def initialize_driver():
    """Initializes the Chrome driver with the appropriate settings."""
    ua = UserAgent()
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode.
    chrome_options.add_argument(f"user-agent={ua.random}")  # Set the user agent.
    chrome_options.add_argument("--disable-notifications")  # Disable notifications.
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-css")
    # Re-enable JavaScript if necessary for dynamic content loading
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--disable-third-party-cookies")
    chrome_options.add_argument("--enable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1280,800")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


