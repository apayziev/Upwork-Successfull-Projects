import os
import time
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from dotenv import load_dotenv
from params import LOGIN_URL
from login import log_in

# Load environment variables
load_dotenv()

def setup_driver():
    """Set up and return a configured Chrome WebDriver"""
    chrome_options = uc.ChromeOptions()
    
    # Add experimental options
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-service-autorun')
    chrome_options.add_argument('--password-store=basic')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--force-device-scale-factor=1')
    chrome_options.add_argument('--force-device-width=1024')
    chrome_options.add_argument('--force-device-height=768')
    chrome_options.add_argument('--window-size=1024,768')
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Set up fake user agent
    ua = UserAgent()
    user_agent = ua.random
    chrome_options.add_argument(f'user-agent={user_agent}')
    
    # Initialize the undetected Chrome WebDriver with specific window size
    driver = uc.Chrome(options=chrome_options)
    
    # Force window size after browser creation
    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
        'width': 1024,
        'height': 768,
        'deviceScaleFactor': 1.0,
        'mobile': False
    })
    
    # Set window size using Selenium as well
    driver.set_window_size(1024, 768)
    
    # Set timeouts
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)
    
    return driver

def main():
    driver = None
    try:
        # Initialize driver
        driver = setup_driver()
        
        # Navigate to login page and log in
        driver.get(LOGIN_URL)
        time.sleep(3)
        log_in(driver)
        
        # Wait after login to ensure session is established
        time.sleep(10)
        
        # Start scraping
        from scraper import MemberScraper
        scraper = MemberScraper(driver)
        scraper.scrape_members('members_urls.txt')
        
    except Exception as e:
        print(f"Error: {str(e)}")
            
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    main()
