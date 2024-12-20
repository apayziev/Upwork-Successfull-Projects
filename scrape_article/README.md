# Installation guide
1. Create environment inside scrape_article folder:<br/>
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

4. Enter article_scrapper folder: `cd article_scrapper`

5. Run the script: `scrapy crawl article -o output.json -t json`

<strong>Enjoy the program!</strong>😉