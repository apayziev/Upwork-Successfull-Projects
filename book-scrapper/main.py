import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor
from requests import Session
from urllib3.util import Retry
from tqdm import tqdm

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0",
]


def get_book_info(url):
    """Get book info from Amazon book page."""

    # Select a random user agent from the list
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.google.com",
    }

    # Create a Retry object with the desired retry settings
    retries = Retry(
        total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )

    # Create a Session object and pass the Retry object to the Session object's mount method
    session = Session()
    session.mount("http://", requests.adapters.HTTPAdapter(max_retries=retries))

    # Introduce a delay of 2 seconds between requests
    time.sleep(2)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as e:
        print(f"Error accessing URL {url}: {e}")
        return None

    title = soup.find("span", {"id": "productTitle"}).text.strip()
    subtitle_element = soup.find("span", {"id": "productSubtitle"})
    if subtitle_element:
        subtitle = subtitle_element.text.strip()
        full_title = f"{title} {subtitle}"
    else:
        full_title = title

    author_elements = soup.find_all("span", {"class": "author notFaded"})
    authors = []
    for author_element in author_elements:
        link_element = author_element.find(
            "a", {"class": "a-link-normal contributorNameID"}
        )
        if link_element:
            authors.append(link_element.text.strip())
        else:
            link_element = author_element.find("a", {"class": "a-link-normal"})
            authors.append(link_element.text.strip())

    year_published = (
        soup.find("div", {"id": "rpi-attribute-book_details-publication_date"})
        .find(
            "div",
            {"class": "a-section a-spacing-none a-text-center rpi-attribute-value"},
        )
        .text
    ).strip()

    image_element = soup.find("img", {"id": "ebooksImgBlkFront"})
    if not image_element:
        image_element = soup.find("img", {"id": "imgBlkFront"})
    if image_element:
        image_url = image_element["src"]
    else:
        image_url = ""

    return {
        "full_title": full_title,
        "authors": authors,
        "year_published": year_published,
        "image_url": image_url,
        "url": url,
    }


def main():
    """Main function."""
    with open("book_urls.txt", "r") as file:
        urls = file.readlines()

    with open("book_info.txt", "w") as outfile:
        with open("failed_urls.txt", "w") as failed_urls_file:
            with ProcessPoolExecutor() as executor:
                results = [executor.submit(get_book_info, url) for url in urls]
                for result in tqdm(results):
                    book_info = result.result()
                    if book_info is None:
                        failed_urls_file.write(f"{book_info['url']}\n")
                    else:
                        outfile.write(f"{book_info['full_title']}\n")
                        outfile.write(", ".join(book_info["authors"]))
                        outfile.write(f"\n{(book_info['year_published'])}\n")
                        outfile.write(f"{book_info['image_url']}\n")
                        outfile.write("\n")


if __name__ == "__main__":
    main()
