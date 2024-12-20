# Solicitation Details Scraper

This Python-based web scraping tool automates the extraction of solicitation details from [Georgia's procurement website](https://fscm.teamworks.georgia.gov/psc/supp/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL?&/), capturing information like solicitation type, title, summary, due dates, and contact details, and saving it in a JSON format. 
It's designed for analysts, researchers, and businesses interested in procurement opportunities in Georgia.

## Description

This scraper aims to streamline the collection of procurement data, which is typically a manual and time-consuming task. By automating this process, the tool facilitates easier analysis of procurement opportunities, tracking of solicitation updates, and optimization of the bidding process. Utilizing Selenium for web interactions, it ensures even dynamically loaded content is accurately captured.

[Watch the video](https://youtu.be/nxqJRmmkX8U)

## Getting Started

### Dependencies

- Python 3.8+
- Selenium
- WebDriver Manager


Developed and tested on Windows 11, this project should be compatible with Linux and macOS with the appropriate Python environment setup.

# Installation guide

1. Create an environment inside the project folder:<br/>
For Win:
    `python -m venv env`<br/>
For macOS:
    `virtualenv venv`

2. Activate environment:<br/>
For Win: 
    `.\env\Scripts\activate`<br />
For MacOS: 
    `source venv/bin/activate`

3. Installing all required packages:
    `pip install -r requirments.txt`
   

5. Run the following command to download gifs:
    `python georgia.py`

6. Enjoy the program.🫡

## How it Works
Built with Selenium, the scraper mimics user interactions on the target website, navigating listings, waiting for content to load, extracting detailed information from each page and outputs the data to **solicitations.json** in the project directory.

## Contributing
Improvements and extensions are welcome. For feature suggestions or bug reports, please open an issue; for direct contributions, submit a pull request with your proposed changes.
