# The **Automated Diamond Info Scraper from [StoneAlgo](https://www.stonealgo.com/diamond-search/s/61d4cdbba724958f931981b246448e33)** 

## Overview
I developed a robust and efficient web scraper for a client on Upwork to extract information on over 4k+ diamonds from a specialized website. The project's success underscores my ability to deliver quality web scraping solutions that handle significant volumes of data.

## [Project video link](https://www.youtube.com/watch?v=7-a5e9hEBpw)

## Key Challenges 

- **Website Complexity** The target diamond website had a complex structure and dynamic elements, requiring careful navigation and data extraction strategies.

- **Data Volume:** Processing thousands of diamond details demanded an optimized approach to ensure timely completion.

- **Rate Limiting (Potential):** The possibility of website-side rate limiting (requests being blocked if sent too frequently) necessitated adjustments to the scraper's behavior.

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

4. Run the following command to download diamond urls:
    `python main.py`

5. Enjoy the program.🫡!

## Technologies Used

- **Python:** Primary programming language.

- **Selenium WebDriver:** Enabled programmatic browser control for interacting with the website and extracting data dynamically.

- **pandas:** Powerful data manipulation and analysis library for efficiently organizing the extracted diamond information.

## Speed Optimization Techniques

- **Multithreading:** Implemented multithreading using Python's ThreadPoolExecutor to concurrently scrape multiple diamond pages, significantly boosting speed

- **Efficient XPath Selectors:** Optimized XPath queries to precisely target the desired data elements, minimizing unnecessary HTML parsing and improving performance.

- **HTTP Headless Mode:** Configured the scraper to run in headless browser mode, reducing resource consumption and speeding up execution.

- **Respectful Pauses (if applicable):** If needed, I incorporated strategic delays or adjusted request patterns to avoid triggering the website's rate-limiting mechanisms.

## Results
- Successfully scraped detailed data for over 4,000 diamonds, providing the client with valuable insights.
- Significantly increased scraping speed due to the implemented optimizations.
- Reduced scraping time by approximately [66%], compared to an initial unoptimized version.

## Code refactoring is not finished yet...🔃
