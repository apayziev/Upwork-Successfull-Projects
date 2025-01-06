import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv

import params

# Load environment variables
load_dotenv()

def wait_for_cloudflare(driver, timeout=30):
    """Wait for Cloudflare security check to complete"""
    print("Waiting for Cloudflare security check...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if "Just a moment..." not in driver.title:
            print("Cloudflare check passed")
            return True
        time.sleep(1)
    
    print("Timed out waiting for Cloudflare")
    return False

def wait_for_page_load(driver):
    """Wait for page to be fully loaded"""
    print("Waiting for page to load completely...")
    start_time = time.time()
    while time.time() - start_time < 30:
        if driver.execute_script("return document.readyState") == "complete":
            return True
        time.sleep(2)
    return False

def check_login_success(driver, timeout=30):
    """Check if login was successful"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_url = driver.current_url
        if "login.circle.so" not in current_url and "sign_in" not in current_url:
            return True
        time.sleep(2)
    return False

def log_in(driver, email=None, password=None):
    """
    Log into Circle Community platform using provided credentials
    """
    try:
        # Use environment variables if credentials not provided
        email = email or os.getenv('CIRCLE_EMAIL')
        password = password or os.getenv('CIRCLE_PASSWORD')
        
        if not email or not password:
            raise ValueError("Email and password must be provided either as parameters or environment variables")

        print(f"Attempting to log in with email: {email}")
        
        # Wait for Cloudflare check to complete
        if not wait_for_cloudflare(driver):
            print("Current URL:", driver.current_url)
            print("Current page title:", driver.title)
            print("Page source:", driver.page_source[:1000])
            raise TimeoutException("Cloudflare security check did not complete")
        
        # Wait for page to be fully loaded
        print("Waiting for page to load completely...")
        if not wait_for_page_load(driver):
            print("Warning: Page might not be fully loaded")
        
        # Additional wait after page load
        time.sleep(5)
        
        # Switch to default content in case of iframes
        driver.switch_to.default_content()
        
        try:
            # Wait for and fill email field
            print("Looking for email field...")
            email_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, params.EMAIL_INPUT_XPATH))
            )
            print("Found email field, entering email...")
            email_field.clear()
            email_field.send_keys(email)
            time.sleep(2)

            # Wait for and fill password field
            print("Looking for password field...")
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, params.PASSWORD_INPUT_XPATH))
            )
            print("Found password field, entering password...")
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(2)

            # Find and click the submit button
            print("Looking for sign in button...")
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, params.SIGN_IN_BUTTON_XPATH))
            )
            
            print("Found submit button, attempting to click...")
            
            # Try multiple click methods
            try:
                submit_button.click()
            except:
                try:
                    driver.execute_script("arguments[0].click();", submit_button)
                except:
                    try:
                        ActionChains(driver).move_to_element(submit_button).click().perform()
                    except Exception as e:
                        print(f"All click methods failed: {str(e)}")
                        raise

            # Wait for login completion
            print("Waiting for login completion...")
            if check_login_success(driver):
                print("Login successful!")
                return True
            else:
                print("Login might have failed. Current URL:", driver.current_url)
                print("Page title:", driver.title)
                return False

        except Exception as e:
            print(f"Login failed with error: {str(e)}")
            print("Current URL:", driver.current_url)
            print("Current page title:", driver.title)
            print("Page source:", driver.page_source[:1000])
            raise

    except Exception as e:
        print(f"Login failed with error: {str(e)}")
        raise