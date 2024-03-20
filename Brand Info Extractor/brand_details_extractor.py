from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

import config



def extract_brand_info(driver, brand_url):
    """Scrapes the brand from the given URL."""
    driver.get(f"{brand_url}/about#tabs")
    WebDriverWait(driver, 8).until(EC.presence_of_all_elements_located((By.XPATH, config.ELEMENTS)))
    try:
        brand_name = driver.find_element(By.XPATH, config.BRAND_NAME_XPATH).text.strip()
    except NoSuchElementException:
        brand_name = "Unknown"
    try:
        brand_description = driver.find_element(By.XPATH, config.BRAND_DESCRIPTION_XPATH).text.strip()
    except NoSuchElementException:
        brand_description = "None"
    try:
        categories = driver.find_elements(By.XPATH, config.CATEGORIES_XPATH)
        categories = [category.text.strip() for category in categories]
    except NoSuchElementException:
        categories = "None"
    try:
        best_of_thingtesting = driver.find_element(By.XPATH, config.BEST_OF_THINGTESTING_XPATH).text.strip()
    except NoSuchElementException:
        best_of_thingtesting = "None"
    try:
        ships_to = driver.find_elements(By.XPATH, config.SHIPS_TO_XPATH)
        ships_to = [ship.text.strip() for ship in ships_to] if ships_to else "None"
    except NoSuchElementException:
        ships_to = "None"
    try:
        website_url = driver.find_element(By.XPATH, config.WEBSITE_URL_XPATH).text.strip()
    except NoSuchElementException:
        website_url = "None"
    try:
        socials = driver.find_elements(By.XPATH, config.SOCIALS_XPATH)
        socials = [social.get_attribute("href") for social in socials] if socials else "None"
    except NoSuchElementException:
        socials = "None"
    try:
        headquarters = driver.find_elements(By.XPATH, config.HEADQUARTERS_XPATH)
        headquarters = [headquarter.text.strip() for headquarter in headquarters if not headquarter.text.strip() == "Headquarters"] if headquarters else "None"
    except NoSuchElementException:
        headquarters = "None"
    try:
        # This is a bit tricky because the founded date is not always present.
        founded = driver.find_element(By.XPATH, config.FOUNDED_XPATH).text.strip().split("\n")[1]
    except NoSuchElementException:
        founded = "None"
    try:
        # This is a bit tricky because the founded date is not always present.
        launched = driver.find_element(By.XPATH, config.LAUNCHED_XPATH).text.strip().split("\n")[1]
    except NoSuchElementException:
        launched = "None"
    try:
        founders = driver.find_elements(By.XPATH, config.FOUNDERS_XPATH)
        founders = [founder.text.strip() for founder in founders] if founders else "None"
    except NoSuchElementException:
        founders = "None"
    try:
        certifications = driver.find_elements(By.XPATH, config.CERTIFICATIONS_XPATH)
        certifications = [certification.text.strip() for certification in certifications] if certifications else "None"
    except NoSuchElementException:
        certifications = "None"

    return {
        "Brand URL": brand_url,
        "Brand Name": brand_name,
        "Brand Description": brand_description,
        "Categories": categories,
        "Best of Thingtesting": best_of_thingtesting,
        "Ships to": ships_to,
        "Website URL": website_url,
        "Socials": socials,
        "Headquarters": headquarters,
        "Founded": founded,
        "Launched": launched,
        "Founders": founders,
        "Certifications": certifications
    }