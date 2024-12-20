# TAAN Member Information Web Scraper (2k)

This web scraper is specifically designed to collect member information from the Trade Association of Nepal (TAAN) **[website](https://www.taan.org.np/members)**. It efficiently extracts various details about TAAN members, providing valuable insights into the organization's membership base. 

## Features

The scraper is capable of extracting the following member details from TAAN's website:

- Organization Name
- Registration Number
- VAT Number
- Address
- Country
- Website URL
- Email
- Telephone Number
- Mobile Number
- Fax
- PO Box
- Key Person
- Establishment Date

## Primary Packages
    - Scrapy: Scraping the content
    - Pandas: Used for data manipulation and for saving the scraped information into an Excel file.


## Installation guide

1. Create environment inside project folder:<br/>
For Win:
    `python -m venv env`<br/>
For MacOS:
    `virtualenv venv`

2. Activate environment:<br/>
For Win: 
    `.\env\Scripts\activate`<br />
For MacOS: 
    `source venv/bin/activate`

3. Installing all required packages:
    `pip install -r requirments.txt`

## Disclaimer

Use this scraper with responsibility. Ensure you comply with TAAN's website terms of service and any relevant data usage regulations.

## Contributing

We welcome contributions! If you have improvements or find issues, feel free to submit pull requests or open issues.
