from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service 


from login import log_in
from anime_downloader import download_all_anime_gifs

# Set proxy
proxy_to_use = "162.248.225.181:80"

proxy = {
    "httpProxy": proxy_to_use,
    "ftpProxy": proxy_to_use,
    "sslProxy": proxy_to_use,
    "proxyType": "MANUAL",
}


chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
chrome_options.add_argument("--disable-notifications")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.maximize_window()


if __name__ == "__main__":
    log_in(driver)
    download_all_anime_gifs(driver)