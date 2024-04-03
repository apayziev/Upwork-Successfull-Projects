from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)
from retrying import retry
from driver_settings import initialize_driver


def wait_for_element_clickable(driver, locator, timeout=10):
    """Waits for an element to be clickable on the page before returning it."""
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def click_load_more_button(driver):
    load_more_button_xpath = "//button[contains(@class, 'search-listings-module_load-more_OwyvW')]"
    load_more_button = wait_for_element_clickable(driver, (By.XPATH, load_more_button_xpath), timeout=5)
    driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
    driver.execute_script("arguments[0].click();", load_more_button)

def extract_product_links(search_term):
    driver = initialize_driver()
    driver.get(f"https://www.takealot.com/all?qsearch={search_term}")
    clicks = 0
    product_links = set()
    
    try:
        cookies_button = driver.find_element(By.XPATH, "//button[text() = 'Got it']")
        cookies_button.click()
    except (NoSuchElementException, StaleElementReferenceException):
        pass  # Or retry if desired
    
    while True:
        try:
            click_load_more_button(driver)
            
            new_links = {link.get_attribute("href") for link in driver.find_elements(By.XPATH, '//*[contains(@class, "product-card-module_product-anchor_TUCBV")]')}
            if not new_links.issubset(product_links):
                product_links.update(new_links)
            
            clicks += 1
            print(f"Clicked 'Load More' {clicks} times.")

        except TimeoutException:
            print("No more items to load or 'Load More' button not clickable.")
            break

    search_term = search_term.lower().replace(" ", "_")
    
    with open(f"product_links_{search_term}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(product_links))
    
    driver.quit()
