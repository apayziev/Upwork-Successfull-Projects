from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from scrape_diamond_urls import scrape_diamond_urls

def initialize_driver():
    """Initializes the Chrome driver with the appropriate settings."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode.
    chrome_options.add_argument("--disable-notifications")  # Disable notifications.
    chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    return driver

if __name__ == "__main__":
    base_url = "https://www.stonealgo.com/diamond-search/s/nt18606778a73268011ee7c087e8fe2773b"
    initialized_driver = initialize_driver()
    scrape_diamond_urls(base_url, initialized_driver)