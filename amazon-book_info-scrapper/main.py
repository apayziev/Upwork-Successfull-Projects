import time
import random
import requests
from bs4 import BeautifulSoup
from requests import Session
from concurrent.futures import ProcessPoolExecutor
from urllib3.util import Retry
from tqdm import tqdm
from requests.adapters import HTTPAdapter

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
    session.mount("http://", HTTPAdapter(max_retries=retries))

    # Introduce a delay of 2 seconds between requests
    time.sleep(2)

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")

        # Extract book title from HTML
        try:
            title = soup.find("span", {"id": "productTitle"}).text.strip()
        except AttributeError:
            print(f" Error: Could not find book title for URL {url}")
            return None

        # Extract book authors from HTML
        try:
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
        except AttributeError:
            print(f"Error: Could not find book authors for URL {url}")
            return None
        # Extract year of publication from HTML
        try:
            year_published = (
                soup.find("div", {"id": "rpi-attribute-book_details-publication_date"})
                .find(
                    "div",
                    {
                        "class": "a-section a-spacing-none a-text-center rpi-attribute-value"
                    },
                )
                .text
            ).strip()
        except AttributeError:
            print(f"Error: Could not find year of publication for URL {url}")
            return None

        # Extract image URL from HTML
        try:
            image_element = soup.find("img", {"id": "ebooksImgBlkFront"})
            if not image_element:
                image_element = soup.find("img", {"id": "imgBlkFront"})
            image_url = image_element["src"]
        except AttributeError:
            print(f"Error: Could not find image URL for URL {url}")

        return {
            "title": title,
            "authors": authors,
            "year_published": year_published,
            "image_url": image_url,
        }

    print(f" Error: Could not get book info for URL {url}")
    return None


def main():
    """Main function."""
    with open("book_urls.txt", "r") as file:
        urls = file.readlines()

    with ProcessPoolExecutor() as executor:
        book_infos = list(tqdm(executor.map(get_book_info, urls), total=len(urls)))

    # Filter out None values
    book_infos = list(filter(None, book_infos))

    with open("book_infos.txt", "w") as file:
        for book_info in book_infos:
            file.write(f"{book_info['title']}\n")
            file.write(", ".join(book_info["authors"]))
            file.write(f"\n{book_info['year_published']}\n")
            file.write(f"{book_info['image_url']}\n")
            file.write("\n")


if __name__ == "__main__":
    main()
