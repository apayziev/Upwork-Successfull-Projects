import os
import pandas as pd
import threading

from brand_links_extractor import (
    extract_brand_links, 
    scrape_brand_and_append
)
from driver_settings import initialize_driver

if __name__ == "__main__":
    initialized_driver = initialize_driver()
    extract_brand_links(initialized_driver)
    
    with open("thingtesting_brand_links.txt", "r", encoding="utf-8") as file:
        brand_links = file.readlines()

    data = []
    lock = threading.Lock()  # Create a lock to manage data access
    threads = []
    semaphore = threading.Semaphore(5)  # Limit the number of concurrent threads to 5

    for index, brand_link in enumerate(brand_links):
        thread = threading.Thread(target=scrape_brand_and_append, args=(brand_link, data, lock, semaphore))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()  

    df = pd.DataFrame(data)

    # Save the data to a excel file.
    df.to_excel("thingtesting_data.xlsx", index=False)

    # Close the driver.
    initialized_driver.quit()