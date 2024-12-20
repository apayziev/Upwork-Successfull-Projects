import os
import logging
import multiprocessing as mp
import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)
from selenium.webdriver.support.select import Select

from driver_settings import initialize_driver
from search_terms import search_terms

def wait_for_element(driver, locator, timeout=10):
    """Waits for an element to be located on the page before returning it."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

def extract_quantity(message):
    """Extracts the available quantity from the given message."""
    if "have" in message and "available" in message:
        start_index = message.find("have ") + 5
        end_index = message.find(" available")
        available_quantity = message[start_index:end_index]
        return available_quantity.strip()
    return None

def get_product_info(driver, product_link, search_term):
    """Extracts the product information from the product page."""
    try:
        driver.get(product_link)

        # Wait for main product section
        wait_for_element(driver, (By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "pdp-main-panel", " " ))]'), timeout=5)

        product_url = driver.current_url

        try:
            cookies_button = driver.find_element(By.XPATH, "//button[text() = 'Got it']")
            cookies_button.click()
        except (NoSuchElementException, StaleElementReferenceException):
            pass  # Or retry if desired

        try:
            login_button = driver.find_element(By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "modal-module_close-button_asjao", " " ))]')
            login_button.click()
        except NoSuchElementException:
            pass

        try:
            product_name = driver.find_element(By.XPATH, '//h1').text.strip()
        except NoSuchElementException:
            product_name = None
            logging.warning("Product name not found")

        try:
            product_price = driver.find_element(By.XPATH, '//span[@class="currency plus currency-module_currency_29IIm" and @data-ref="buybox-price-main"]').text.strip()
        except NoSuchElementException:
            product_price = None

        # Add to cart with enhanced wait
        try:
            add_to_cart_button = wait_for_element(driver, (By.XPATH, "//a[contains(@class, 'add-to-cart-button-module_add-to-cart-button_1a9gT')]"), timeout=5)
            add_to_cart_button.click()
        except (NoSuchElementException, TimeoutException):
            return {
                "product_url": product_url,
                "search_term": search_term,
                "product_name": product_name,
                "product_price": product_price,
                "available_quantity": None
            }

        # Wait for other elements involved in cart interactions
        time.sleep(1)  # Small delay after actions
        go_to_cart_button = wait_for_element(driver, (By.XPATH, '//button[@class="button checkout-now dark"]'), timeout=5)
        go_to_cart_button.click()

        quantity_button = wait_for_element(driver, (By.XPATH, '//*[(@id = "cart-item_undefined")]'), timeout=5)
        quantity_button.click()

        time.sleep(1)
        quantity_dropdown = wait_for_element(driver, (By.ID, "cart-item_undefined"), timeout=5)
        select_object = Select(quantity_dropdown)
        select_object.select_by_visible_text("10+")

        # Send keys with care
        quantity_input = driver.find_element(By.XPATH, '//*[(@id = "cart-item_undefined")]')
        quantity_input.clear()  # Clear any existing values
        quantity_input.send_keys('9999')

        time.sleep(2)
        update_button = wait_for_element(driver, (By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "quantity-update", " " ))]'), timeout=5)
        update_button.click()

        # Get message with error handling
        time.sleep(2)
        try:
            notification = driver.find_element(By.XPATH, '//div[@class="cell auto message-container"]//div[@class="message alert-banner-module_message_2sinO"]').text.strip()
            available_quantity = extract_quantity(notification)
        except NoSuchElementException:
            logging.warning("Quantity notification not found")

        # remove item from cart
        remove_button = driver.find_element(By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "remove-item", " " ))]')
        remove_button.click()

        return {
            "product_url": product_url,
            "search_term": search_term,
            "product_name": product_name,
            "product_price": product_price,
            "available_quantity": available_quantity
        }
    except NoSuchElementException as e:
        logging.error("Error processing %s: %s", product_link, e)
        return {
            "product_url": product_link,
            "search_term": search_term,
            "product_name": None,
            "product_price": None,
            "available_quantity": None
        }

def process_product_link(product_link, search_term, queue):
    """Processes a single product link and puts the result into a queue"""
    try:
        driver = initialize_driver()  # Initialize a new driver within the process
        product_info = get_product_info(driver, product_link, search_term)
        queue.put(product_info)
    finally:
        driver.quit()

def scrape_product_info(search_term):
    """Scrapes product information for the given search term."""
    search_term_ = search_term.lower().replace(" ", "_")
    product_links_folder = "product_links"
    with open(f"{product_links_folder}/product_links_{search_term_}.txt", "r", encoding="utf-8") as f:
        product_links = f.read().splitlines()

    num_processes = max(1, mp.cpu_count() - 1)  # Reserve one CPU for the main process

    with mp.Manager() as manager:
        queue = manager.Queue()  # Queue to store results from processes

        with mp.Pool(processes=num_processes) as pool:
            for product_link in product_links:
                pool.apply_async(process_product_link, args=(product_link, search_term, queue))

            pool.close()
            pool.join()  # Wait for all processes to finish

            # Collect results from the queue
            product_info = []
            while not queue.empty():
                product_info.append(queue.get())

    # Create a DataFrame from the product information
    df = pd.DataFrame(product_info)

    current_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    outputs_folder = 'outputs'
    file_name = f'{outputs_folder}/product_info_{search_term_}_{current_date}.csv'

    # Check if the outputs folder exists, create it if it doesn't
    if not os.path.exists(outputs_folder):
        os.makedirs(outputs_folder)

    # Save the DataFrame to a CSV file in the outputs folder
    df.to_csv(file_name, index=False)


if __name__ == "__main__":
    for search_term in search_terms:
        scrape_product_info(search_term)
        print(f"Finished scraping product information for '{search_term}'.")

