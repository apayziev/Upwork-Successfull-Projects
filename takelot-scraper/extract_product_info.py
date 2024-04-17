import os
import logging
import multiprocessing as mp
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.support.select import Select

from driver_settings import initialize_driver
from search_terms import search_terms

# Setup logging configuration
logging.basicConfig(filename='scraping_logs.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def wait_for_element(driver, locator, timeout=10):
    """Waits for an element to be located on the page before returning it."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

def extract_quantity(messages):
    quantity = None
    for message in messages:
        try:
            if "but we only have" in message:
                start_index = message.find("but we only have") + 17
                end_index = message.find(" available", start_index)
                quantity = message[start_index:end_index]
                break
        except Exception as e:
            logging.error(f"Error in extract_quantity: {str(e)}")
    return quantity.strip() if quantity else None

def retry_operation(func, retries=3, *args, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Attempt {attempt+1} failed: {str(e)}")
            if attempt == retries - 1:
                raise

def get_product_info(driver, product_link, search_term):
    """Extracts the product information from the product page."""
    try:
        driver.get(product_link)

        wait_for_element(driver, (By.CSS_SELECTOR, 'div.pdp-main-panel'), timeout=5)

        product_url = driver.current_url

        # try:
        #     cookies_button = driver.find_element(By.XPATH, "//button[text() = 'Got it']")
        #     cookies_button.click()
        # except (NoSuchElementException, StaleElementReferenceException):
        #     pass  # Or retry if desired

        # try:
        #     login_button = driver.find_element(By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "modal-module_close-button_asjao", " " ))]')
        #     login_button.click()
        # except NoSuchElementException:
        #     pass

        try:
            product_name = driver.find_element(By.CSS_SELECTOR, 'h1').text.strip()
        except NoSuchElementException:
            product_name = None

        try:
            product_price = driver.find_element(By.CSS_SELECTOR, 'span.currency.plus[data-ref="buybox-price-main"]').text.strip()
        except NoSuchElementException:
            product_price = None

        try:
            add_to_cart_button = wait_for_element(driver, (By.CSS_SELECTOR, 'a[class*="add-to-cart-button-module_add-to-cart-button_1a9gT"]'), timeout=5)
            add_to_cart_button.click()
        except (NoSuchElementException, TimeoutException):
            return {
                "product_url": product_url,
                "search_term": search_term,
                "product_name": product_name,
                "product_price": product_price,
                "available_quantity": None
            }
        
        go_to_cart_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.cell.content-wrapper > button.checkout-now.dark'))
        )
        go_to_cart_button.click()

        quantity_button = wait_for_element(driver, (By.ID, "cart-item_undefined"), timeout=5)
        quantity_button.click()

        driver.implicitly_wait(1)
        quantity_dropdown = wait_for_element(driver, (By.ID, "cart-item_undefined"), timeout=5)
        select_object = Select(quantity_dropdown)
        select_object.select_by_visible_text("10+")

        # Send keys with care
        quantity_input = driver.find_element(By.ID, 'cart-item_undefined')
        quantity_input.clear()  # Clear any existing values
        quantity_input.send_keys('9999')

        driver.implicitly_wait(1)
        update_button = wait_for_element(driver, (By.CSS_SELECTOR, '*[class*="quantity-update"]'), timeout=5)
        update_button.click()

        # Get message with error handling
        driver.implicitly_wait(2)
        try:
            notification_elements = driver.find_elements(By.CSS_SELECTOR, 'div.cell.auto.message-container div.message.alert-banner-module_message_2sinO')
            messages = [element.text.strip() for element in notification_elements]
            available_quantity = extract_quantity(messages)
        except NoSuchElementException:
            logging.info("No notification found")
            available_quantity = None
           
            
        driver.implicitly_wait(2)
        try:
            remove_buttons = driver.find_elements(By.CSS_SELECTOR, '*[class*="remove-item"]')
            for button in remove_buttons:
                driver.execute_script("arguments[0].click();", button)
                WebDriverWait(driver, 10).until(EC.staleness_of(button))
        except NoSuchElementException:
            logging.info("No remove button found")
        except Exception as e:
            logging.error(f"Error clicking remove buttons: {str(e)}")

        return {
            "product_url": product_url,
            "search_term": search_term,
            "product_name": product_name,
            "product_price": product_price,
            "available_quantity": available_quantity
        }
    except NoSuchElementException as e:
        print("Element not found", product_link)
        return {
            "product_url": product_link,
            "search_term": search_term,
            "product_name": None,
            "product_price": None,
            "available_quantity": None
        }

def process_product_link(product_link, search_term, file_path, driver):
    try:
        product_info = retry_operation(get_product_info, 2, driver, product_link, search_term)
        with open(file_path, 'a', encoding='utf-8', newline='') as f:
            pd.DataFrame([product_info]).to_csv(f, header=f.tell()==0, index=False)
    except Exception as e:
        logging.error(f"Failed to process {product_link}: {str(e)}")

def worker(product_links, search_term, file_path):
    driver = initialize_driver()
    try:
        for product_link in product_links:
            process_product_link(product_link, search_term, file_path, driver)
    finally:
        driver.quit()
        

def scrape_product_info(search_term):
    search_term_ = search_term.lower().replace(" ", "_")
    if search_term_[0] == '"' and search_term_[-1] == '"':
        search_term_ = search_term_[1:-1] + "_with_quotes"
    outputs_folder = 'outputs'
    current_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    file_name = f'{outputs_folder}/product_info_{search_term_}_{current_date}.csv'
    if not os.path.exists(outputs_folder):
        os.makedirs(outputs_folder)
    product_links_folder = "product_links"
    try:
        with open(f"{product_links_folder}/product_links_{search_term_}.txt", "r", encoding="utf-8") as f:
            product_links = f.read().splitlines()
    except FileNotFoundError:
        logging.error("Product links file not found for search term '%s'", search_term)
        return
    
    num_processes = min(3, len(product_links))
    chunk_size = len(product_links) // num_processes
    chunks = [product_links[i:i + chunk_size] for i in range(0, len(product_links), chunk_size)]
    with mp.Pool(processes=num_processes) as pool:
        pool.starmap(worker, [(chunk, search_term, file_name) for chunk in chunks])

if __name__ == "__main__":
    for search_term in search_terms:
        scrape_product_info(search_term)
        print(f"Finished scraping product information for '{search_term}'.")
