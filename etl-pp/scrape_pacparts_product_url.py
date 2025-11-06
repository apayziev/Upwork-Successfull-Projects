import asyncio
import csv

from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

from patchright.async_api import async_playwright

# -------------------- Configuration --------------------
@dataclass
class ScraperConfig:
    """Configuration for the scraper."""
    base_url: str = "https://www.pacparts.com/casio"
    user_data_dir: str = "./browser_profile"
    part_file: str = "casio_part_urls.csv"
    model_file: str = "casio_model_urls.csv"
    failed_pages_file: str = "failed_pages.txt"
    max_retries: int = 3
    retry_delay: int = 5
    page_timeout: int = 60000
    page_size: int = 60
    delay_between_pages: int = 2
    progress_interval: int = 10


@dataclass
class ScrapingStats:
    """Statistics for scraping session."""
    total_pages: int = 0
    part_urls_count: int = 0
    model_urls_count: int = 0
    failed_pages: list[int] = None
    
    def __post_init__(self):
        if self.failed_pages is None:
            self.failed_pages = []
    
    @property
    def total_urls(self) -> int:
        return self.part_urls_count + self.model_urls_count


class URLClassifier:
    """Classifies URLs into part or model categories."""
    
    PART_URL_PREFIX = "https://www.pacparts.com/casio-cas"
    
    @classmethod
    def is_part_url(cls, url: str) -> bool:
        """Check if URL is a part URL."""
        return url.startswith(cls.PART_URL_PREFIX)
    
    @classmethod
    def split_urls(cls, urls: list[str]) -> Tuple[list[str], list[str]]:
        """Split URLs into part and model lists."""
        part_urls = [url for url in urls if cls.is_part_url(url)]
        model_urls = [url for url in urls if not cls.is_part_url(url)]
        return part_urls, model_urls


class CSVWriter:
    """Handles writing URLs to CSV files."""
    
    @staticmethod
    def append_urls(urls: list[str], filename: str) -> None:
        """Append URLs to CSV file."""
        if not urls:
            return
        
        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for url in urls:
                writer.writerow([url])
    
    @staticmethod
    def delete_if_exists(filename: str) -> None:
        """Delete file if it exists."""
        file_path = Path(filename)
        if file_path.exists():
            file_path.unlink()
            print(f"Deleted existing {filename}")


class FailedPagesManager:
    """Manages failed pages tracking."""
    
    @staticmethod
    def save(failed_pages: list[int], filename: str) -> None:
        """Save failed page numbers to file."""
        if not failed_pages:
            return
        
        with open(filename, "w") as f:
            for page_num in failed_pages:
                f.write(f"{page_num}\n")
        print(f"Saved {len(failed_pages)} failed pages to {filename}")


class ProgressReporter:
    """Handles progress reporting."""
    
    @staticmethod
    def print_progress(page_num: int, stats: ScrapingStats, config: ScraperConfig) -> None:
        """Print progress update."""
        if page_num % config.progress_interval != 0:
            return
        
        progress = (page_num / stats.total_pages) * 100
        print(f"\nProgress: {page_num}/{stats.total_pages} ({progress:.1f}%)")
        print(f"Part URLs: {stats.part_urls_count}, Model URLs: {stats.model_urls_count}")
        
        if stats.failed_pages:
            print(f"Failed pages so far: {len(stats.failed_pages)}")
    
    @staticmethod
    def print_summary(stats: ScrapingStats, config: ScraperConfig) -> None:
        """Print scraping summary."""
        print(f"\n{'='*50}")
        print(f"Scraping complete!")
        print(f"Pages processed: 1 to {stats.total_pages}")
        print(f"Total part URLs collected: {stats.part_urls_count}")
        print(f"Total model URLs collected: {stats.model_urls_count}")
        print(f"Total URLs: {stats.total_urls}")
        print(f"Failed pages: {len(stats.failed_pages)}")
        
        ProgressReporter._print_file_info(config.part_file, stats.part_urls_count)
        ProgressReporter._print_file_info(config.model_file, stats.model_urls_count)
        
        print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*50}")
    
    @staticmethod
    def _print_file_info(filename: str, url_count: int) -> None:
        """Print file size information."""
        if url_count > 0 and Path(filename).exists():
            file_size = Path(filename).stat().st_size / (1024 * 1024)
            print(f"\n{filename}: {file_size:.2f} MB")


class PageScraper:
    """Handles scraping of individual pages."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
    
    async def get_total_pages(self, page) -> int:
        """Get total number of pages from pagination."""
        url = self._build_url(1)
        
        for attempt in range(self.config.max_retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", 
                              timeout=self.config.page_timeout)
                await page.wait_for_selector(".pager", timeout=10000)
                
                last_page_link = await page.query_selector(".pager .last-page a")
                if last_page_link:
                    total_pages = int(await last_page_link.get_attribute("data-page"))
                    print(f"Total pages found: {total_pages}")
                    return total_pages
                
                return 1
                
            except Exception as e:
                if not await self._handle_retry(attempt, e, "get total pages"):
                    raise
        
        return 1
    
    async def scrape_urls(self, page_num: int, page) -> Optional[list[str]]:
        """Extract all product URLs from a single page."""
        url = self._build_url(page_num)
        
        for attempt in range(self.config.max_retries):
            try:
                print(f"Scraping page {page_num} (attempt {attempt + 1}/{self.config.max_retries})...")
                
                await page.goto(url, wait_until="domcontentloaded", 
                              timeout=self.config.page_timeout)
                await page.wait_for_selector(".product-item", timeout=15000)
                
                urls = await self._extract_urls(page)
                print(f"Page {page_num}: Found {len(urls)} URLs")
                return urls
                
            except Exception as e:
                if not await self._handle_retry(attempt, e, f"page {page_num}"):
                    print(f"Failed to scrape page {page_num} after all retries")
                    return None
        
        return None
    
    def _build_url(self, page_num: int) -> str:
        """Build URL for specific page number."""
        return (f"{self.config.base_url}?viewmode=grid&orderby=5"
                f"&pagesize={self.config.page_size}&pagenumber={page_num}")
    
    async def _extract_urls(self, page) -> list[str]:
        """Extract product URLs from page."""
        product_links = await page.query_selector_all(".product-item .product-title a")
        
        urls = []
        for link in product_links:
            href = await link.get_attribute("href")
            if href:
                full_url = f"https://www.pacparts.com{href}" if href.startswith("/") else href
                urls.append(full_url)
        
        return urls
    
    async def _handle_retry(self, attempt: int, error: Exception, context: str) -> bool:
        """Handle retry logic. Returns True if should retry, False otherwise."""
        print(f"Attempt {attempt + 1}/{self.config.max_retries} failed to {context}: {error}")
        
        if attempt < self.config.max_retries - 1:
            wait_time = self.config.retry_delay * (2 ** attempt)
            print(f"Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)
            return True
        
        return False


class CasioScraper:
    """Main scraper orchestrator."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.stats = ScrapingStats()
        self.page_scraper = PageScraper(config)
        self.csv_writer = CSVWriter()
        self.url_classifier = URLClassifier()
        self.progress_reporter = ProgressReporter()
        self.failed_pages_manager = FailedPagesManager()
    
    def prepare_output_files(self) -> None:
        """Prepare output files by deleting existing ones."""
        for filename in [self.config.part_file, self.config.model_file]:
            self.csv_writer.delete_if_exists(filename)
        print()
    
    def process_urls(self, urls: list[str]) -> None:
        """Process and save URLs to appropriate files."""
        part_urls, model_urls = self.url_classifier.split_urls(urls)
        
        self.stats.part_urls_count += len(part_urls)
        self.stats.model_urls_count += len(model_urls)
        
        self.csv_writer.append_urls(part_urls, self.config.part_file)
        self.csv_writer.append_urls(model_urls, self.config.model_file)
        
        print(f"  -> Appended {len(part_urls)} part URLs and {len(model_urls)} model URLs")
    
    async def scrape_page(self, page_num: int, page) -> bool:
        """Scrape a single page. Returns True if successful, False otherwise."""
        urls = await self.page_scraper.scrape_urls(page_num, page)
        
        if urls is None:
            self.stats.failed_pages.append(page_num)
            print(f"⚠️  Skipping page {page_num} - will save for later retry")
            return False
        
        if urls:
            self.process_urls(urls)
        
        return True
    
    async def run(self) -> None:
        """Run the scraper."""
        self.prepare_output_files()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.config.user_data_dir,
                channel="chrome",
                headless=False,
                no_viewport=True,
            )
            
            page = await browser.new_page()
            
            try:
                await self._scrape_all_pages(page)
                self._finalize()
                
            except KeyboardInterrupt:
                self._handle_interruption()
                
            except Exception as e:
                self._handle_error(e)
                
            finally:
                await browser.close()
    
    async def _scrape_all_pages(self, page) -> None:
        """Scrape all pages."""
        self.stats.total_pages = await self.page_scraper.get_total_pages(page)
        
        for page_num in range(1, self.stats.total_pages + 1):
            await self.scrape_page(page_num, page)
            
            self.progress_reporter.print_progress(page_num, self.stats, self.config)
            
            if page_num < self.stats.total_pages:
                await asyncio.sleep(self.config.delay_between_pages)
    
    def _finalize(self) -> None:
        """Finalize scraping session."""
        self.progress_reporter.print_summary(self.stats, self.config)
        self.failed_pages_manager.save(self.stats.failed_pages, 
                                       self.config.failed_pages_file)
    
    def _handle_interruption(self) -> None:
        """Handle keyboard interruption."""
        print("\n\nScraping interrupted by user")
        print(f"Part URLs: {self.stats.part_urls_count}, Model URLs: {self.stats.model_urls_count}")
        self.failed_pages_manager.save(self.stats.failed_pages, 
                                       self.config.failed_pages_file)
    
    def _handle_error(self, error: Exception) -> None:
        """Handle fatal error."""
        print(f"\nFatal error occurred: {error}")
        print(f"Part URLs: {self.stats.part_urls_count}, Model URLs: {self.stats.model_urls_count}")
        self.failed_pages_manager.save(self.stats.failed_pages, 
                                       self.config.failed_pages_file)


async def main():
    """Main entry point."""
    config = ScraperConfig()
    scraper = CasioScraper(config)
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())