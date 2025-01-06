import os
import csv
import time
import random
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import params
from login import log_in
from main import setup_driver

class MemberScraper:
    def __init__(self, driver):
        self.driver = driver
        self.output_file = f'members_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        self.failed_urls_file = f'failed_urls_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        self.base_headers = [
            'Profile URL',
            'Full Name',
            'Role',
            'LinkedIn',
            'Twitter',
            'Facebook',
            'Instagram',
            'TikTok'
        ]
        self.max_other_links = 0  # Will be updated as we find more links
        self.failed_urls = []
        self.csv_headers = self.base_headers.copy()  # Will be extended dynamically

    def update_headers_if_needed(self, num_other_links):
        """Update CSV headers if we find more other social links than before"""
        if num_other_links > self.max_other_links:
            # Add new headers for the additional other links
            for i in range(self.max_other_links + 1, num_other_links + 1):
                self.csv_headers.append(f'Other Social Link {i}')
            self.max_other_links = num_other_links

    def wait_for_profile_load(self):
        """Wait for profile page to load past Cloudflare"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Check for Cloudflare challenge
                if any(text in self.driver.page_source for text in ["Verifying you are human", "Just a moment"]):
                    wait_time = 20 if retry_count == 0 else 10
                    time.sleep(wait_time)
                    
                    # Check if we're still on Cloudflare
                    if any(text in self.driver.page_source for text in ["Verifying you are human", "Just a moment"]):
                        retry_count += 1
                        if retry_count < max_retries:
                            self.driver.refresh()
                            continue
                    else:
                        time.sleep(2)
                        return True
                else:
                    return True
                    
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5)
                    continue
        
        return False

    def extract_member_info(self, url):
        """Extract member information from their profile page"""
        try:
            self.driver.get(url)
            
            # Wait for Cloudflare and page load
            if not self.wait_for_profile_load():
                raise TimeoutException("Profile page did not load past Cloudflare")
            
            # Additional wait for dynamic content
            time.sleep(5)
            
            # Wait for profile content to load
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, params.MEMBER_XPATHS['full_name']))
                )
            except TimeoutException:
                raise
            
            # Extract member information
            full_name = self.get_text_by_xpath(params.MEMBER_XPATHS['full_name'])
            
            role = self.get_text_by_xpath(params.MEMBER_XPATHS['role'])
            
            # Get social links with detailed debugging
            social_links = []
            
            # Try first XPath part
            try:
                social_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'profile-drawer__about__heading')]/following-sibling::div//a")
                if social_elements:
                    for elem in social_elements:
                        href = elem.get_attribute('href')
                        if href:
                            social_links.append(href)
            except Exception as e:
                print(f"Error with first XPath: {str(e)}")

            # Try second XPath part
            try:
                social_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'profile-social-links')]//a")
                if social_elements:
                    for elem in social_elements:
                        href = elem.get_attribute('href')
                        if href:
                            social_links.append(href)
            except Exception as e:
                print(f"Error with second XPath: {str(e)}")

            # Try finding any links in the profile area
            try:
                profile_area = self.driver.find_element(By.XPATH, "//div[contains(@class, 'profile-drawer') or contains(@class, 'profile-container')]")
                all_links = profile_area.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    href = link.get_attribute('href')
                    if href and any(domain in href.lower() for domain in ['linkedin', 'twitter', 'facebook', 'instagram']):
                        social_links.append(href)
            except Exception as e:
                print(f"Error finding general social links: {str(e)}")

            # Format social links by platform
            social_links_by_platform = {
                'LinkedIn': '',
                'Twitter': '',
                'Facebook': '',
                'Instagram': '',
                'TikTok': ''
            }
            
            other_links = []
            for link in set(social_links):  # Remove duplicates
                link_lower = link.lower()
                if 'linkedin.com' in link_lower:
                    social_links_by_platform['LinkedIn'] = link
                elif 'twitter.com' in link_lower or 'x.com' in link_lower:
                    social_links_by_platform['Twitter'] = link
                elif 'facebook.com' in link_lower:
                    social_links_by_platform['Facebook'] = link
                elif 'instagram.com' in link_lower:
                    social_links_by_platform['Instagram'] = link
                elif 'tiktok.com' in link_lower:
                    social_links_by_platform['TikTok'] = link
                else:
                    other_links.append(link)
            
            # Update headers if we found more other links than before
            self.update_headers_if_needed(len(other_links))
            
            # Add other links to the result dictionary
            result = {
                'Profile URL': url,
                'Full Name': full_name,
                'Role': role,
                'LinkedIn': social_links_by_platform['LinkedIn'],
                'Twitter': social_links_by_platform['Twitter'],
                'Facebook': social_links_by_platform['Facebook'],
                'Instagram': social_links_by_platform['Instagram'],
                'TikTok': social_links_by_platform['TikTok']
            }
            
            # Add other links to result
            for i, link in enumerate(other_links, 1):
                result[f'Other Social Link {i}'] = link
            
            return result
            
        except Exception as e:
            print(f"Error scraping profile {url}: {str(e)}")
            print("Current URL:", self.driver.current_url)
            print("Page title:", self.driver.title)
            print("Page source excerpt:", self.driver.page_source[:500])
            return None

    def get_text_by_xpath(self, xpath, default=''):
        """Safely get text from an element by XPath"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            return element.text.strip()
        except NoSuchElementException:
            return default

    def scrape_members(self, urls_file):
        """Scrape information for all members in the URLs file"""
        try:
            # Read URLs from file
            with open(urls_file, 'r') as f:
                urls = [url.strip() for url in f.readlines() if url.strip()]
            
            # Create/open the CSV file with write mode first to write headers
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.csv_headers)
                writer.writeheader()
            
            # Now open in append mode for data
            with open(self.output_file, 'a', newline='', encoding='utf-8') as csvfile:
                for url in urls:
                    try:
                        # Add random delay between requests (5-15 seconds)
                        time.sleep(random.uniform(5, 15))
                        
                        member_info = self.extract_member_info(url)
                        if member_info:
                            # Ensure we have all needed columns
                            writer = csv.DictWriter(csvfile, fieldnames=self.csv_headers)
                            writer.writerow(member_info)
                        else:
                            self.failed_urls.append(url)
                            
                        # If we get a rate limit error, wait longer
                        if "Too Many Requests" in self.driver.page_source:
                            time.sleep(30)  # Wait 30 seconds before next request
                            
                    except Exception as e:
                        self.failed_urls.append(url)
                        if "Too Many Requests" in str(e):
                            time.sleep(30)  # Wait 30 seconds on rate limit error
            
            # Write failed URLs if any
            if self.failed_urls:
                with open(self.failed_urls_file, 'w') as f:
                    for url in self.failed_urls:
                        f.write(f"{url}\n")
            
        except Exception as e:
            print(f"Error: {str(e)}")

def main():
    driver = None
    try:
        # Initialize driver
        driver = setup_driver()
        
        # Log in first
        print("\nLogging in...")
        driver.get(params.LOGIN_URL)
        if not log_in(driver):
            raise Exception("Login failed")
        
        # Initialize scraper and start scraping
        scraper = MemberScraper(driver)
        print("\nStarting member scraping...")
        scraper.scrape_members('members_urls.txt')
        
        print(f"\nScraping completed! Data saved to {scraper.output_file}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
