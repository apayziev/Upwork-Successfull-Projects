from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import requests
from lxml import html
import json
import fitz
import csv
from docx import Document
import pandas as pd
from datetime import datetime 
import boto3
import pandas as pd
import io
import traceback
from pprint import pprint

aws_access_key_id = ''
aws_secret_access_key = ''
# Initialize the boto3 client
s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
# Specify your bucket name
bucket_name = 'gov-bids2'
state='pennsylvania'


def get_page_links(url):
    # Set up the Selenium WebDriver
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # This argument configures Chrome to run in headless mode.
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=chrome_options)
    

    # Open the web page
    driver.get(url)
    page_links = []

    ### Sets any neecessary options on the webpage, navigates to table with open public solicitaitons
    all_button=WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//option[text()="ALL"]'))) #button to display all the listings
    all_button.click()
    time.sleep(2)
    ### Gets all links for the bid pages
    tds= driver.find_elements(By.XPATH,'//table[@sort="UpdatedDate DESC"]/tbody/tr/td[1]/a')
    print('count of urls is ',len(tds))
    for td in tds:
        page_links.append(td.get_attribute('href'))
    ### If distinct URLs for each page link do not exist, ignore this function

    return page_links

def last_csv_links(filename):
    links = []
    try:
        with open(filename, "r") as f:
            reader = csv.reader(f)
            next(reader)  # Skip the header
            for row in reader:
                links.append(row[0])
    except FileNotFoundError:
        # If the file does not exist, return an empty list
        return []
    pprint(links)
    return links

def store_link(filename,link):
    with open(filename,"a")as f:
        writer=csv.writer(f)
        writer.writerow([link])


# methods to get data from the files 
def extract_text_from_pdf(file_stream):
    text = ''
    with fitz.open(stream=file_stream, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(file_stream):
    doc = Document(file_stream)
    return '\n'.join([paragraph.text for paragraph in doc.paragraphs])

def extract_text_from_xlsx(file_stream):
    df = pd.read_excel(file_stream)
    return df.to_csv(index=False)

def extract_text_from_csv(file_stream):
    df = pd.read_csv(file_stream)
    return df.to_csv(index=False)

def extract_store_file_data(urls,solicitation_number):
    files_text=[]
    for url in urls:
        try:
            # we are getting related url so joining it with main url
            url="https://www.emarketplace.state.pa.us/"+url
            response = requests.get(url)
            content_type = response.headers['content-type']
            file_stream = io.BytesIO(response.content)
            
            # Determine file type
            if 'pdf' in content_type:
                filetype = 'pdf'
                filetext = extract_text_from_pdf(file_stream)
            elif 'document' in content_type:
                filetype = 'docx'
                filetext = extract_text_from_docx(file_stream)
            elif 'excel' in content_type or 'spreadsheetml.sheet' in content_type:
                filetype = 'xlsx'
                filetext = extract_text_from_xlsx(file_stream)
            elif 'csv' in content_type:
                filetype = 'csv'
                filetext = extract_text_from_csv(file_stream)
            else:
                filetype=url.split('.')[-1]
                if filetype == "com":
                    raise Exception("Not doument link")
                filetext="N/a"
            filename = url.split('=')[-1].replace("%20","_")
            creation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # document_content = response.content

            # # Define the S3 key (path in the bucket)
            # s3_key = f"prod_gold/{state}/{solicitation_number}/documents/{filename}"
            # # Convert document content to bytes if it's not already in bytes format
            # if not isinstance(document_content, bytes):
            #     document_content = bytes(document_content, 'utf-8')

            # # Upload the document to S3
            # s3.put_object(Bucket=bucket_name, Key=s3_key, Body=document_content)
            data= {
                'filename': filename,
                'filetype': filetype,
                'filetext': filetext,
                'creation_date': creation_date
            }
            files_text.append(data)
        except Exception as e:
            # print('error in parsing url',str(e))
            traceback.print_exc()
    return files_text

def scrape_solicitations(base_url, link, state, save_files,last_urls):
    ### Should take in only one link 
        
    ### Check if link has been scraped before
    if link not in last_urls:
        response = requests.get(link)
        tree = html.fromstring(response.content)
        solicitation_data = {}

        solicitation_data['state'] = state
        # Example for 'main_category', adjust the XPath as needed for your actual HTML structure
        solicitation_data['main_category'] = tree.xpath('//input[@checked="checked"]/following-sibling::label/text()')[0]

        # Replace 'YourTextHere' with actual text for other fields, similar to the 'main_category' example
        solicitation_data['solicitation_type'] = tree.xpath('//strong[contains(text(), "Types")]/../following-sibling::td/span/text()')[0]
        solicitation_data['main_title'] = tree.xpath('//strong[contains(text(), "Solicitation/Project Title")]/../following-sibling::td/span/text()')[0]
        solicitation_data['solicitation_summary'] = tree.xpath('//strong[contains(text(), "Description")]/../following-sibling::td/span/text()')[0]
        solicitation_number=tree.xpath('//strong[contains(text(), "Solicitation/Project#")]/../following-sibling::td/span/text()')[0]
        solicitation_data['id'] = tree.xpath('//strong[contains(text(), "Solicitation/Project#")]/../following-sibling::td/span/text()')[0]
        solicitation_data['alternate_id']="N/a"
        solicitation_data['status']="N/a"
        solicitation_data['due_date_local'] = tree.xpath('//strong[contains(text(), "Solicitation Due Date")]/../following-sibling::td/span/text()')[0]
        solicitation_data['due_date_time_local'] = tree.xpath('//strong[contains(text(), "Solicitation Due Time")]/../following-sibling::td/span/text()')[0]
        solicitation_data['issuing_agency'] = tree.xpath('//strong[contains(text(), "Department/Agency")]/../following-sibling::td/span/text()')[0]
        solicitation_data['procurement_officer_buyer_name'] = tree.xpath('//strong[contains(text(), "First Name")]/../following-sibling::td/span/text()')[0] + " " + tree.xpath('//strong[contains(text(), "Last Name")]/../following-sibling::td/span/text()')[0]
        solicitation_data['procurement_officer_email'] = tree.xpath('//strong[contains(text(), "Email")]/../following-sibling::td/span/text()')[0]
        solicitation_data['procurement_officer_phone'] = tree.xpath('//strong[contains(text(), "Phone Number")]/../following-sibling::td/span/text()')[0]
        solicitation_data['additional_instructions']="N/a"
        solicitation_data['issue_date'] = tree.xpath('//strong[contains(text(), "Date Prepared")]/../following-sibling::td/span/text()')[0]
        ### Get attachements 
        file_links=tree.xpath('//table[contains(@id,"MainBody_dgFileList")]//a/@href')
        print('File Links found',len(file_links))
        ### Parse out attachements into all_texts, see example in code 
        solicitation_data['pdf_texts']=extract_store_file_data(file_links,solicitation_number)
        solicitation_data['project_cost_class']='N/a'
        solicitation_data['Location']=tree.xpath('//strong[contains(text(), "County")]/../following-sibling::td[1]/span/text()')[0]
        solicitation_data['miscellaneous']="N/a"
        solicitation_data['link']=link
        # print(solicitation_data)


        ### Parse out meta data and append to 'solicitation_data' json dictionary 
        solicitation_data_bytes = json.dumps(solicitation_data).encode('utf-8')
        ### Save all data to s3 
        # json_s3_key = f"prod_gold/{state}/{solicitation_number}/json/{solicitation_number}.json"
        # s3.put_object(Bucket=bucket_name, Key=json_s3_key, Body=solicitation_data_bytes)
        store_link("last_pennsylvania.csv",link)
    else:
        print("Link already processed")
    
if __name__== "__main__":
    base_url="https://www.emarketplace.state.pa.us/Search.aspx"
    last_csv_filename="last_pennsylvania.csv"
    last_urls=last_csv_links("./last_pennsylvania.csv")
    links=get_page_links(base_url)
    for link in links:
        scrape_solicitations(base_url,link,"pennsylvania",True,last_urls)
        print("Proccesed url",link)
    # scrape_solicitations(base_url,'https://www.emarketplace.state.pa.us/Solicitations.aspx?SID=034020141',"Pennsylvania",True,last_urls)
