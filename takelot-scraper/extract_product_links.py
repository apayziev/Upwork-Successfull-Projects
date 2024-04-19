import os
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
from search_terms import search_terms

def wait_for_element(driver, locator, timeout=10):
    """Wait for an element to be present and visible."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def click_load_more_button(driver):
    load_more_button_xpath = "//button[contains(@class, 'search-listings-module_load-more_OwyvW')]"
    try:
        load_more_button = wait_for_element(driver, (By.XPATH, load_more_button_xpath), timeout=5)
        driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
        driver.execute_script("arguments[0].click();", load_more_button)
        return True  # Button was successfully clicked
    except TimeoutException:
        return False  # Button could not be clicked (possibly because it doesn't exist)

def extract_product_links(search_term):
    driver = initialize_driver()
    try:
        driver.get("https://www.takealot.com/")
        clicks = 0
        product_links = set()
        
        try:
            cookies_button = driver.find_element(By.XPATH, "//button[text() = 'Got it']")
            cookies_button.click()
        except (NoSuchElementException, StaleElementReferenceException):
            pass  # Or retry if desired
        
        # search input
        try:
            search_input = driver.find_element(By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "search-field", " " ))]')
            search_input.send_keys(search_term)
        except NoSuchElementException:
            print("Search input not found.")

        # search button
        try:
            search_button = driver.find_element(By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "search-icon", " " ))]')
            search_button.click()
        except NoSuchElementException:
            print("Search button not found.")
            
        
        load_more_button_xpath = "//button[contains(@class, 'search-listings-module_load-more_OwyvW')]"
        # check if the "Load More" button exists on the page
        if not driver.find_elements(By.XPATH, load_more_button_xpath):
            # driver.refresh()
            driver.implicitly_wait(2)
            product_links = {link.get_attribute("href") for link in driver.find_elements(By.XPATH, '//*[contains(@class, "product-card-module_product-anchor_TUCBV")]')}

        while True:
            button_clicked = click_load_more_button(driver)
            if not button_clicked:
                print("No more items to load or 'Load More' button not clickable.")
                break  # Exit the loop if the button wasn't clicked
            
            new_links = {link.get_attribute("href") for link in driver.find_elements(By.XPATH, '//*[contains(@class, "product-card-module_product-anchor_TUCBV")]')}
            if not new_links.issubset(product_links):
                product_links.update(new_links)
            
            clicks += 1
            print(f"Clicked 'Load More' for {search_term} | {clicks} times.")
        
        search_term_ = search_term.lower().replace(" ", "_")
        product_links_folder = "product_links"
        if search_term_[0] == '"' and search_term_[-1] == '"':
            search_term_ = search_term_[1:-1]
            file_path = f"{product_links_folder}/product_links_{search_term_}_with_quotes.txt"
        else:
            file_path = f"{product_links_folder}/product_links_{search_term_}.txt"

        # Check if the product_links folder exists, create it if it doesn't
        if not os.path.exists(product_links_folder):
            os.makedirs(product_links_folder)

        # Now it saves the product links to the specified folder
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(product_links))
    finally:
        driver.quit()

if __name__ == "__main__":
    for search_term in search_terms:
        extract_product_links(search_term)
