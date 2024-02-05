import json
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def initialize_driver():
    """Initializes the Chrome driver with the appropriate settings."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode.
    chrome_options.add_argument("--disable-notifications")  # Disable notifications.
    chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    return driver

def wait_for_element(driver, locator, timeout=10):
    """Waits for an element to be located on the page before returning it."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

def extract_contact_details(driver):
    """
    Extracts procurement officer's email and phone from a modal, popup, or iframe.
    """
    try:
        contact_button = driver.find_element(By.XPATH, '//*[@id="SCP_COSP_WK_FL_IMAGE_1$0"]')
        contact_button.click()
        # Use the wait_for_element function for the iframe
        frame = wait_for_element(driver, (By.XPATH, "//iframe[contains(@src, '/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL')]"))
        driver.switch_to.frame(frame)
        
        procurement_officer_email = driver.find_element(By.ID, 'SCP_P_AUCDTL_VW_EMAILID').text.strip()
        procurement_officer_phone = driver.find_element(By.ID, 'SCP_P_AUCDTL_VW_PHONE').text.strip()
        
    except Exception as e:
        print(f"Error extracting contact details: {e}")
        procurement_officer_email, procurement_officer_phone = "N/a", "N/a"
    
    finally:
        driver.get(driver.current_url)
    
    return procurement_officer_email, procurement_officer_phone


def extract_attachments(driver):
    pass



def scrape_page(driver, url):
    """ Scrapes the page and returns a list of dictionaries containing the data."""
    driver.get(url)
    wait_for_element(driver, (By.XPATH, '//*[contains(concat(" ", @class, " "), "ps_grid-flex")]'))
    rows = driver.find_elements(By.XPATH, '//*[contains(concat(" ", @class, " "), "ps_grid-flex")]/tbody/tr')
    data = []

    for row_num in range(len(rows)):
        row_id = f"SCP_PUB_AUC_VW$0_row_{row_num}"
        driver.find_element(By.ID, row_id).click()
        wait_for_element(driver, (By.ID, "win0divSCP_P_AUCDTL_VW_$0"))

        state = "georgia"  # Default value
        main_category = "N/a"  # Default value
        solicitation_type = get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_AUC_TYPE$0"]')
        main_title = get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_AUC_NAME$0"]')
        solicitation_summary = get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_DESCRLONG$0"]')
        id = get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_AUC_ID$0"]')
        alternate_id = "N/a"  # Default value
        status = get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_AUC_STATUS$0"]')
        due_date_local = get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_SCP_END_DATE_CHAR$0"]').split(" ")[0]
        due_date_time_local = " ".join(get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_SCP_END_DATE_CHAR$0"]').split(" ")[1:])
        issuing_agency = get_text(driver, '//*[@id="BUS_UNIT_AUC_VW_DESCR$0"]')
        procurement_officer_buyer_name = " ".join(get_text(driver, '//*[@id="PO_OPRDEFN_VW_OPRDEFNDESC$0"]').split()[:-1])
        issue_date = get_text(driver, '//*[@id="SCP_P_AUCDTL_VW_SCP_STRT_DATE_CHAR$0"]')
        bid_link = driver.current_url
        additional_instructions = "N/a"  # Default value
        project_cost_class = "N/a"  # Default value
        location = "N/a"  # Default value
        miscellaneous = "N/a"  # Default value

        # Extract contact details
        procurement_officer_email, procurement_officer_phone = extract_contact_details(driver)

        data.append({
            "state": state,
            "main_category": main_category,
            "solicitation_type": solicitation_type,
            "main_title": main_title,
            "solicitation_summary": solicitation_summary,
            "id": id,
            "alternate_id": alternate_id,
            "status": status,
            "due_date_local": due_date_local,
            "due_date_time_local": due_date_time_local,
            "issuing_agency": issuing_agency,
            "procurement_officer_buyer_name": procurement_officer_buyer_name,
            "procurement_officer_email": procurement_officer_email,
            "procurement_officer_phone": procurement_officer_phone,
            "issue_date": issue_date,
            "bid_link": bid_link,
            "additional_instructions": additional_instructions,
            "project_cost_class": project_cost_class,
            "location": location,
            "miscellaneous": miscellaneous
        })

        driver.get(url)  # Reload the main page to reset the state for the next iteration.

    return data



def get_text(driver, xpath):
    """Returns the text of an element identified by the xpath."""
    element = wait_for_element(driver, (By.XPATH, xpath))
    return element.text.strip() if element else ""

def main():
    base_url = "https://fscm.teamworks.georgia.gov/psc/supp/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL"
    driver = initialize_driver()
    try:
        solicitation_data = scrape_page(driver, base_url)
        with open("solicitations.json", "w") as file:
            json.dump(solicitation_data, file, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
