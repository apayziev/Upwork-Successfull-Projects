import random
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent



def initialize_driver():
    """Initializes the Chrome driver with the appropriate settings."""
    ua = UserAgent()
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode.
    chrome_options.add_argument(f"user-agent={ua.random}")  # Set the user agent.
    chrome_options.add_argument("--disable-notifications")  # Disable notifications.
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    return driver
