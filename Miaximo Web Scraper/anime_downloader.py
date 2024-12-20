import os
import re
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from concurrent.futures import ThreadPoolExecutor

from params import (
    directory_name, animation_xpath, mixamo_home_page_xpath, next_page_button_xpath,
    animation_title_xpath, animation_description_xpath, animation_gif_url_xpath
)

# Sanitize and truncate the description for the filename
def sanitize_description(desc, max_length=50):
    desc = desc.replace("Description: ", "").strip()
    # Remove non-file-safe characters
    desc = re.sub(r'[<>:"/\\|?*]', '', desc)
    # Truncate to the maximum length
    if len(desc) > max_length:
        desc = desc[:max_length].rstrip()
    return desc

def navigate_to_next_page(driver):
    try:
        # Wait for the next page button to be clickable
        next_page_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, next_page_button_xpath))
        )
        
        # Scroll the button into view
        driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button)
        
        # Additional wait for the button to become clickable after scrolling
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, next_page_button_xpath))
        )

        # Use ActionChains to click the button if direct click fails
        ActionChains(driver).move_to_element(next_page_button).click().perform()
        
        return True
    except TimeoutException:
        # Handle the case where the button doesn't become clickable within the timeout
        print("Next page button not clickable.")
        return False
    except NoSuchElementException:
        # Handle the case where the button is not found
        print("No next page button found.")
        return False

def download_gif(animation, index):
    title_element = animation.find_element(By.XPATH, animation_title_xpath)
    title = title_element.text.strip().replace("/", "")

    gif_url_element = animation.find_element(By.XPATH, animation_gif_url_xpath)
    gif_url = gif_url_element.get_attribute("src")
        
    try:
        description = animation.find_element(By.XPATH, animation_description_xpath).get_attribute('textContent').strip().replace("/", "")
    except NoSuchElementException:
        description = "No description available."
    description = sanitize_description(description)
        
    response = requests.get(gif_url, timeout=10)
    if response.status_code == 200:
        filename = f"{index:04d}-{title}-{description}.gif"
        with open(os.path.join(directory_name, filename), "wb") as f:
            f.write(response.content)


def download_all_anime_gifs(driver):
    """
    Download all the GIFs from the Mixamo website
    """
    # Create the directory if it doesn't exist
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    # Initialize ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=5)

    index = 1
    while True:
        animations = driver.find_elements(By.XPATH, animation_xpath)

        # Create a list to store futures for the download tasks
        download_futures = []
        
        # Loop through animations and submit download tasks to the executor
        for animation in animations:
            future = executor.submit(download_gif, animation, index)
            download_futures.append(future)
            index += 1

        # Wait for all download tasks to complete
        for future in download_futures:
            future.result()

        # Navigate to the next page
        if not navigate_to_next_page(driver):
            break
        
        # Wait for the animations to be loaded on the new page
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, mixamo_home_page_xpath))
        )

    # Shutdown the executor
    executor.shutdown(wait=True)
        
        