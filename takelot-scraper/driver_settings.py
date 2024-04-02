"""
Module docstring goes here.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent


def initialize_driver():
    """Initializes the Chrome driver with the appropriate settings."""
    ua = UserAgent()
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Run Chrome in headless mode.
    chrome_options.add_argument(f"user-agent={ua.random}")  # Set the user agent.
    chrome_options.add_argument("--disable-notifications")  # Disable notifications.
    chrome_options.add_argument('--disable-gpu')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


