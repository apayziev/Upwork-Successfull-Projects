import os
import time
import json 
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service 
from selenium.common.exceptions import NoSuchElementException
from pprint import pprint

def wait_for_home_page(driver):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[contains(concat(" ", @class, " "), "ps_grid-flex")]'))
    )


def event_details_page_scraper(driver):

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="win0divSCP_P_AUCDTL_VW_$0"]'))
    )




def get_page_links(url):
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless") 
    # chrome_options.add_argument(f'--proxy-server={proxy_server_url}')
    chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
    chrome_options.add_argument("--disable-notifications")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()
   
    driver.get(url)
    solicitations_data = []
   
    try:
        wait_for_home_page(driver)
        
        row_count = len(driver.find_elements(By.XPATH, '//*[contains(concat(" ", @class, " "), "ps_grid-flex")]/tbody/tr'))

        for row_num in range(0, row_count):
            row_id = f"SCP_PUB_AUC_VW$0_row_{row_num}"
            print(row_id)
            # Correct XPath and use a separate variable for the element
            row_element = driver.find_element(By.ID, row_id)
            row_element.click()
            time.sleep(2)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="win0divSCP_P_AUCDTL_VW_$0"]')))
            state = 'georgia'
            main_category = "N/a"
            solicitation_type = driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_AUC_TYPE$0"]').text.strip()
            main_title = driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_AUC_NAME$0"]').text.strip()
            solicitation_summary = driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_DESCRLONG$0"]').text.strip()
            id = driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_AUC_ID$0"]').text.strip()
            alternate_id = "N/a"
            status = driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_AUC_STATUS$0"]').text.strip()
            due_date_local = driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_SCP_END_DATE_CHAR$0"]').text.strip().split(" ")[0]
            due_date_time_local = " ".join(driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_SCP_END_DATE_CHAR$0"]').text.strip().split(" ")[1:])
            issuing_agency = driver.find_element(By.XPATH, '//*[@id="BUS_UNIT_AUC_VW_DESCR$0"]').text.strip()
            procurement_officer_buyer_name = " ".join(driver.find_element(By.XPATH, '//*[@id="PO_OPRDEFN_VW_OPRDEFNDESC$0"]').text.strip().split()[:-1])
            additional_instructions = "N/a"
            project_cost_class = "N/a"
            location = "N/a"
            miscellaneous = "N/a"
            issue_date = driver.find_element(By.XPATH, '//*[@id="SCP_P_AUCDTL_VW_SCP_STRT_DATE_CHAR$0"]').text.strip()
            bid_link = driver.current_url
            
            
            contact_button = driver.find_element(By.XPATH, '//*[@id="SCP_COSP_WK_FL_IMAGE_1$0"]')
            contact_button.click()
            time.sleep(3)
            # Wait for the iframe to be present and switch to it by src attribute
            wait = WebDriverWait(driver, 10)
            # Here we use `contains` to match a part of the src attribute value
            frame = wait.until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, '/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL')]")))
            driver.switch_to.frame(frame)

            # Now that the context is switched to the iframe, locate the email element
            procurement_officer_email = driver.find_element(By.ID, 'SCP_P_AUCDTL_VW_EMAILID').text.strip()
            procurement_officer_phone = driver.find_element(By.ID, 'SCP_P_AUCDTL_VW_PHONE').text.strip()
        
            
            # reload the page
            driver.get(url)

            row_element = driver.find_element(By.ID, row_id)
            row_element.click()
            time.sleep(2)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="win0divSCP_P_AUCDTL_VW_$0"]')))

            view_bid_package_button = driver.find_element(By.XPATH, '//*[@id="SCP_COSP_WK_FL_DESCR2$0"]')
            view_bid_package_button.click()
            time.sleep(3)
            
            # Common base URL part of the src attribute
            common_url_part = 'https://fscm.teamworks.georgia.gov/psc/supp/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL?ICType=Panel&ICElementNum=0&ICStateNum'

            # Wait for the iframe to be present and switch to it using a partial match on the src attribute
            wait = WebDriverWait(driver, 10)
            frame = wait.until(EC.presence_of_element_located((By.XPATH, f"//iframe[starts-with(@src, '{common_url_part}')]")))
            driver.switch_to.frame(frame)
            time.sleep(5)

            # Locate the table container by its XPath
            table_container = driver.find_element(By.XPATH, '//*[@id="win0divEOATT_G1L1_DVW_GROUPBOX3$0"]')

          
            rows = table_container.find_elements(By.XPATH, './/tr')
            rows_count = len(rows)
            descriptions = []
            for row_index in range(0, rows_count):
                description = rows[row_index]
                description_xpath = f".//div[@id='win0divEOATT_G1L3_DVW_EOATT_FIELD4${row_index}']"
                
                description_element = description.find_element(By.XPATH, description_xpath)
                time.sleep(2)
                descriptions.append(description_element.text.strip())
                print(description_element.text.strip())

           

            
        
            # solicitation_data = {
            #     "state": state,
            #     "main_category": main_category,
            #     "solicitation_type": solicitation_type,
            #     "main_title": main_title,
            #     "solicitation_summary": solicitation_summary,
            #     "id": id,
            #     "alternate_id": alternate_id,
            #     "status": status,
            #     "due_date_local": due_date_local,
            #     "due_date_time_local": due_date_time_local,
            #     "issuing_agency": issuing_agency,
            #     "procurement_officer_buyer_name": procurement_officer_buyer_name,
            #     "procurement_officer_email": procurement_officer_email,
            #     "procurement_officer_phone": procurement_officer_phone,
            #     "additional_instructions": additional_instructions,
            #     "project_cost_class": project_cost_class,
            #     "location": location,
            #     "issue_date": issue_date,
            #     "bid_link": bid_link,
            #     "miscellaneous": miscellaneous
            # }

            # solicitations_data.append(solicitation_data)
            

            # back_button = driver.find_element(By.XPATH, '//*[(@id = "PT_WORK_PT_BUTTON_BACK")]')
            # back_button.click()
            # time.sleep(2)
            driver.get(url)
            # wait_for_home_page(driver)
        
    finally:
        driver.quit()
    for description in descriptions:
        print(description)
    

    # with open("georgia.json", "w") as outfile:
    #     json.dump(solicitations_data, outfile, indent=4)


if __name__ == "__main__":
    base_url = "https://fscm.teamworks.georgia.gov/psc/supp/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL"
    get_page_links(base_url)       