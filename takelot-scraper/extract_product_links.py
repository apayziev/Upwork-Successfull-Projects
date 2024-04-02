import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from driver_settings import initialize_driver


def wait_for_element(driver, locator, timeout=10):
    """Waits for an element to be located on the page before returning it."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))


def extract_product_links(search_term):
    """Extracts the product links from the search results page."""
    driver = initialize_driver()
    driver.set_window_size(200, 250)
    driver.get(f"https://www.takealot.com/all?qsearch={search_term}")

    load_more_button_xpath = "//button[contains(@class, 'search-listings-module_load-more_OwyvW')]"

    try:
        cookies_button = driver.find_element(By.XPATH, "//button[text() = 'Got it']")
        cookies_button.click()
    except (NoSuchElementException, StaleElementReferenceException):
        pass  # Or retry if desired


    clicks = 1

    load_more_button = wait_for_element(driver, (By.XPATH, load_more_button_xpath))

    while True:
        try:

            driver.execute_script("arguments[0].scrollIntoView();", load_more_button)

            # Wait for the button to be clickable
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable(load_more_button))
            load_more_button.click()
            print("clicked", clicks, "times")
            clicks += 1

        except (
            NoSuchElementException,
            ElementClickInterceptedException,
            ElementNotInteractableException,
            TimeoutException,
        ):
            logging.debug("Clicking the button failed. Likely no more items to load.")
            try:
                driver.execute_script("arguments[0].click();", load_more_button)
            except Exception:
                logging.debug("Clicking the button failed. Likely no more items to load.")
                break

    product_links = [
        link.get_attribute("href")
        for link in driver.find_elements(
            By.XPATH,
            '//*[contains(concat( " ", @class, " " ), concat( " ", "product-card-module_product-anchor_TUCBV", " " ))]',
        )
    ]
    
    # remove duplicates
    product_links = list(set(product_links))
    
    search_term = search_term.lower().replace(" ", "_")

    with open(f"product_links_{search_term}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(product_links))

    driver.quit() 


