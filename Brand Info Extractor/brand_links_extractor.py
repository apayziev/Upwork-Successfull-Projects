import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementNotVisibleException


from brand_details_extractor import extract_brand_info
from driver_settings import initialize_driver
import config

def extract_brand_links(driver):
    """Extracts the brand links from the given URL."""
    page_number = 1
    while True:
        page_url = f"https://thingtesting.com/brands?p={page_number}&c=beauty"
        driver.get(page_url)
        brand_elements = driver.find_elements(By.XPATH, config.BRAND_ELEMENTS_LINKS)
        if len(brand_elements) > 0:
            brand_links = [brand_url.get_attribute("href").split("/reviews")[0].strip() for brand_url in brand_elements]
            
            with open("thingtesting_brand_links.txt", "a", encoding="utf-8") as file:
                for brand_link in brand_links:
                    file.write(f"{brand_link}\n")
            print(f"Scraped links from page {page_number}")
            page_number += 1
        else:
            print("No more brand links to scrape.")
            break  # Exit the loop when no more brand links are found

def scrape_brand_and_append(brand_link, data, lock, semaphore):
    """Fetches data for a brand and appends it to the shared data list."""
    semaphore.acquire()  # Wait for a slot to open up
    try:
        initialized_driver = initialize_driver()  # Note: See discussion below
        brand_data = extract_brand_info(initialized_driver, brand_link)
        with lock:  
            data.append(brand_data) 
    except (TimeoutException, ElementNotVisibleException) as e:
        logging.error(f"Error scraping {brand_link}: {e}")

    finally:
        initialized_driver.quit() 
        semaphore.release()  # Release the slot