import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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


def scrape_diamond_info(diamond_url):
    driver = initialize_driver()
    print(f"scraping data from {diamond_url}")
    driver.get(diamond_url)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[70]/div[2]"))

    )
    main_info_base_xpath = "/html/body/div[1]/div[70]/div[2]/div[1]/div[2]"
    diamond_id = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[1]/h1").text.strip()
    diamond_type = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[1]/span[2]").text.strip()
    try:
        price = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[2]/div[4]/p").text.replace("USD", "").strip()
    except:
        price = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[2]/div[2]/div[1]/div[2]/div/span[1]").text

    try:
        estimate_range = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[2]/div[2]/div[2]/div/div[2]/div/span/span").text
    except:
        estimate_range = ""
    
    fair_price = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[4]/div/div[1]/div/div/div/dl/dd/div/div").text.strip()
    
    cert_lab = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[8]/div/div/div/dl/dd/div").text.strip()
    lw_or_cut_score_indentifier = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[4]/div/div[2]/div/div/div/dl/dt/div[1]/button/span[1]").text.strip()
    if lw_or_cut_score_indentifier == "L/W Ratio":
        lw_ratio = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[4]/div/div[2]/div/div/div/dl/dd/div").text.strip()
        cut_score = ""
    elif lw_or_cut_score_indentifier == "Cut Score":
        cut_score = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[4]/div/div[2]/div/div/div/dl/dd/div").text.strip()
        lw_ratio = ""
    visual_carat = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[4]/div/div[3]/div/div/div/dl/dd/div").text.strip()
    shape = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[1]/div/div/div/dl/dd/div").text.strip()
    carat = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[2]/div/div/div/dl/dd/div").text.strip()
    color = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[3]/div/div/div/dl/dd/div").text.strip()
    clarity = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[4]/div/div/div/dl/dd/div").text.strip()
    fluorescence = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[5]/div/div/div/dl/dd/div").text.strip()
    symmetry = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[6]/div/div/div/dl/dd/div").text.strip()
    polish = driver.find_element(By.XPATH, f"{main_info_base_xpath}/div[5]/div[2]/div[7]/div/div/div/dl/dd/div").text.strip()
    image = driver.find_element(By.XPATH, "/html/body/div[1]/div[70]/div[2]/div[1]/div[1]/div/div[2]/div[2]/div[1]/img").get_attribute("src")
    
    price_details = driver.find_element(By.XPATH, "/html/body/div[1]/div[70]/div[2]/section[2]/div/p").text.strip()
    
    gia_report_details_base_xpath = "/html/body/div[1]/div[70]/div[2]/section[3]/div/div[2]/div/div[1]/div[2]/div[2]"
    sertificate_data = driver.find_element(By.XPATH, f"{gia_report_details_base_xpath}/div[1]").text.strip()
    report_number = driver.find_element(By.XPATH, f"{gia_report_details_base_xpath}/div[2]").text.strip()
    measurements = driver.find_element(By.XPATH, f"{gia_report_details_base_xpath}/div[4]").text.strip()

    cut_grade = driver.find_element(By.XPATH, "/html/body/div[1]/div[70]/div[2]/section[3]/div/div[2]/div/div[1]/div[4]/div[2]/div[4]").text.strip()
    

    clarity_characteristics = driver.find_element(By.XPATH, "/html/body/div[1]/div[70]/div[2]/section[3]/div/div[2]/div/div[2]/div[2]/div/div[4]/div[2]").text.strip()
    inscriptions = driver.find_element(By.XPATH, "/html/body/div[1]/div[70]/div[2]/section[3]/div/div[2]/div/div[2]/div[2]/div/div[5]/div[2]").text.strip()
    comments = driver.find_element(By.XPATH, "/html/body/div[1]/div[70]/div[2]/section[3]/div/div[2]/div/div[2]/div[2]/div/div[6]/div[2]").text.strip()
    
    #Proportions
    base_proportions_xpath = "/html/body/div[1]/div[70]/div[2]/section[3]/div/div[2]/div/div[3]"
    if cert_lab == "GIA":
        # scroll to the proportions section
        driver.execute_script("arguments[0].scrollIntoView();", driver.find_element(By.XPATH, base_proportions_xpath))
        # if the button does not exist, it means that the proportions are already shown
        try:
            show_more_button = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[1]")
            driver.execute_script("arguments[0].click();", show_more_button)

            table_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[1]/div").text.strip()
            depth_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[2]/div").text.strip()
            culet = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[10]/div").text.strip()
            try:
                pav_depth = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[3]/div").text.strip() 
            except:
                pav_depth = ""  
            try:
                pav_angle = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[4]/div").text.strip() 
            except:
                pav_angle = ""
            try:
                crown_height = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[5]/div").text.strip() 
            except:
                crown_height = ""
            try:
                crown_angle = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[6]/div").text.strip() 
            except:
                crown_angle = ""
            try:
                lower_half_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[7]/div").text.strip() 
            except:
                lower_half_pct = ""
            try:
                star_lenght_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[8]/div").text.strip() 
            except:
                star_lenght_pct = ""
            try:
                girdle_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[3]/div/div[9]/div").text.strip() 
            except:
                girdle_pct = ""
        except:
            print("No show more button found.")
            show_more_button = None
            table_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[1]/div").text.strip()
            depth_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[2]/div").text.strip()
            culet = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[10]/div").text.strip()
            try:
                pav_depth = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[3]/div").text.strip()
            except:
                pav_depth = ""
            try:
                pav_angle = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[4]/div").text.strip() 
            except:
                pav_angle = ""
            try:
                crown_height = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[5]/div").text.strip() 
            except:
                crown_height = ""
            try:
                crown_angle = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[6]/div").text.strip() 
            except:
                crown_angle = ""
            try:
                lower_half_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[7]/div").text.strip() 
            except:
                lower_half_pct = ""
            try:
                star_lenght_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[8]/div").text.strip()
            except:
                star_lenght_pct = "" 
            try:
                girdle_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[9]/div").text.strip() 
            except:
                girdle_pct = ""
    else:
        table_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[1]/div").text.strip()
        depth_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[2]/div").text.strip()
        culet = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[10]/div").text.strip()
        try:
            pav_depth = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[3]/div").text.strip()
        except:
            pav_depth = ""
        try:
            pav_angle = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[4]/div").text.strip() 
        except:
            pav_angle = ""
        try:
            crown_height = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[5]/div").text.strip() 
        except:
            crown_height = ""
        try:
            crown_angle = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[6]/div").text.strip() 
        except:
            crown_angle = ""
        try:
            lower_half_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[7]/div").text.strip() 
        except:
            lower_half_pct = ""
        try:
            star_lenght_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[8]/div").text.strip()
        except:
            star_lenght_pct = "" 
        try:
            girdle_pct = driver.find_element(By.XPATH, f"{base_proportions_xpath}/div[2]/div[3]/div[9]/div").text.strip() 
        except:
            girdle_pct = ""


   
    data = {
        "Diamond ID": diamond_id,
        "Diamond Type": diamond_type,
        "Price": price,
        "Estimate Range": estimate_range,
        "Fair Price": fair_price,
        "Cert Lab": cert_lab,
        "L/W Ratio": lw_ratio,
        "Cut Score": cut_score,
        "Visual Carat": visual_carat,
        "Shape": shape,
        "Carat": carat,
        "Color": color,
        "Clarity": clarity,
        "Fluorescence": fluorescence,
        "Symmetry": symmetry,
        "Polish": polish,
        "Image URL": image,
        "Price Details": price_details,
        "Sertificate Data": sertificate_data,
        "Report Number": report_number,
        "Measurements": measurements,
        "Cut Grade": cut_grade,
        "Clarity Characteristics": clarity_characteristics,
        "Inscriptions": inscriptions,
        "Comments": comments,
        "Table %": table_pct,
        "Depth %": depth_pct,
        "Culet": culet,
        "Pavilion Depth": pav_depth,
        "Pavilion Angle": pav_angle,
        "Crown Height": crown_height,
        "Crown Angle": crown_angle,
        "Lower Half %": lower_half_pct,
        "Star Lenght %": star_lenght_pct,
        "Girdle %": girdle_pct
    }
    driver.quit()
    return data

def process_diamond(diamond_url, result_list):
    """Scrapes data from a diamond URL and appends results to a shared list."""
    scraped_data = scrape_diamond_info(diamond_url)
    result_list.append(scraped_data)


if __name__ == "__main__":
    with open("diamonds_urls.txt", "r") as f:
        diamond_urls = f.readlines()

    # Result list to store scraped data from all threads
    all_diamond_data = []

    MAX_THREADS = 5
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []  # Store Future objects
        for diamond_url in diamond_urls:
            future = executor.submit(process_diamond, diamond_url, all_diamond_data)
            futures.append(future)

    # Wait for completion and gather results
    for future in futures:
        future.result()

    # Check if the file already exists
    try:
        existing_data = pd.read_excel('natural_diamonds_info.xlsx')
        # Append the new data to the existing DataFrame
        all_diamond_data = existing_data.append(all_diamond_data, ignore_index=True)
    except FileNotFoundError:
        pass  # File doesn't exist yet, proceed to create a new DataFrame

    # Convert the list of dictionaries to a DataFrame
    all_diamond_df = pd.DataFrame(all_diamond_data)

    # Save the combined DataFrame to the Excel file
    all_diamond_df.to_excel('natural_diamonds_info.xlsx', index=False)

        


    
    