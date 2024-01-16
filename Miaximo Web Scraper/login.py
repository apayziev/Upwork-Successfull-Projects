import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import ADOBEUSERNAME, ADOBEPASSWORD

from params import (
    login_button_xpath,
    email_input_xpath, email_continue_button_xpath,
    verification_form_xpath, password_continue_button_xpath,
    password_input_xpath,mixamo_home_page_xpath,
)

from anime_downloader import download_all_anime_gifs

def log_in(driver):
    """
    Log in to Mixamo using the provided credentials
    """
    # Navigate to the Mixamo website or login page
    driver.get("https://www.mixamo.com/")
    driver.implicitly_wait(10)

    # Click the login button
    login_button = driver.find_element(By.XPATH, login_button_xpath)
    login_button.click()
    
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, email_input_xpath))
    )
    email_input.clear()
    email_input.send_keys(ADOBEUSERNAME)
    
    # Click the continue button
    continue_button = driver.find_element(By.XPATH, email_continue_button_xpath)
    continue_button.click()
    
    # click the verification button
    verification_button = driver.find_element(By.XPATH, verification_form_xpath)
    verification_button.click()

    password_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, password_input_xpath))
    )
    password_input.clear()
    password_input.send_keys(ADOBEPASSWORD)

    # Click the continue button
    continue_button = driver.find_element(By.XPATH, password_continue_button_xpath)
    continue_button.click()

    # Wait for the home page to load. 
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, mixamo_home_page_xpath))
    )
    
    current_url = driver.current_url + "?limit=96" # Set the limit to 96 animations per page
    # Navigate to the current URL
    driver.get(current_url)
    
    download_all_anime_gifs(driver) 

