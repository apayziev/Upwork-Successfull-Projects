from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import epected_conditions as EC
import time

def wait_for_element(driver, locator, timeout=10):
    """Waits for an element to be located on the page before returning it."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

def scrape_diamond_urls(base_url, driver):
    driver.get(base_url)

    for i in range(1, 12):
        xpath_for_diamond_shape_button = "/html/body/div[1]/div[24]/div[3]/div[1]/div/div[2]"
        button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath_for_diamond_shape_button))
            )
        button.click() 
        print(f"current url{i}: ", driver.current_url)
            
        change_chape_xpath = f"/html/body/div[1]/div[24]/div[3]/div[1]/div/div[2]/div/ul/li[{i}]"
        change_shape = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, change_chape_xpath))
            )
        change_shape.click()
        time.sleep(5)
        driver.get(driver.current_url)

        wait_for_element(driver, (By.ID, "sa-res_2"))
        diamond_elements = driver.find_elements(By.XPATH, "//div[@id='sa-res_2']/div")
        all_diamond_links = [
            "https://www.stonealgo.com" + element.get_attribute('data-product_link') 
            for element in diamond_elements
        ]

        with open('diamonds_urls.txt', 'a') as f:
            for link in all_diamond_links:
                f.write(link + '\n')
