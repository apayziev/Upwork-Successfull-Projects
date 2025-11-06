import asyncio
import csv
import os
import re
import sys

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from dataclasses import dataclass

from playwright.async_api import async_playwright


# ==================== Configuration ====================
@dataclass
class ScraperConfig:
    """Configuration for the part details scraper."""
    user_data_dir: str = "./browser_profile"
    input_file: str = "casio_part_urls.csv"
    output_file: str = "casio_part_details.csv"
    num_workers: int = 3
    batch_size: int = 1000
    headless: bool = False
    retry_attempts: int = 3
    request_delay: float = 0.3
    batch_pause: int = 3
    page_timeout: int = 15000
    selector_timeout: int = 3000


@dataclass
class GlobalCounter:
    """Global counter for tracking progress."""
    count: int = 0
    total: int = 0


# ==================== Data Models ====================
@dataclass
class PartDetails:
    """Part details data model."""
    part_number: str = ""
    title: str = ""
    manufacturer: str = ""
    availability: str = "available"
    list_price: str = ""
    replacement: str = ""
    associated_models: str = ""
    part_image_url: str = ""
    part_url: str = ""
    total_associated_models_displayed: int = 0
    associated_models_collected: int = 0
    associated_models_matches: str = "False"
    
    @classmethod
    def get_fieldnames(cls) -> List[str]:
        """Get CSV fieldnames."""
        return [
            "part_number", "title", "manufacturer", "availability", "list_price",
            "replacement", "associated_models", "part_image_url", "part_url",
            "total_associated_models_displayed", "associated_models_collected",
            "associated_models_matches"
        ]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for CSV writing."""
        return {
            "part_number": self.part_number,
            "title": self.title,
            "manufacturer": self.manufacturer,
            "availability": self.availability,
            "list_price": self.list_price,
            "replacement": self.replacement,
            "associated_models": self.associated_models,
            "part_image_url": self.part_image_url,
            "part_url": self.part_url,
            "total_associated_models_displayed": self.total_associated_models_displayed,
            "associated_models_collected": self.associated_models_collected,
            "associated_models_matches": self.associated_models_matches
        }


# ==================== Page Extractors ====================
class PartInfoExtractor:
    """Extracts part information from page elements."""
    
    @staticmethod
    async def extract_part_number(page) -> str:
        """Extract part number from page."""
        h1_elem = await page.query_selector(".product-name h1")
        if not h1_elem:
            return ""
        
        h1_text = (await h1_elem.inner_text()).strip()
        if "CAS-" in h1_text:
            return h1_text.split("CAS-")[-1].strip()
        
        return "" if h1_text == "*N/A" else h1_text
    
    @staticmethod
    async def extract_title(page) -> str:
        """Extract title from short description."""
        title_elem = await page.query_selector(".short-description")
        return (await title_elem.inner_text()).strip() if title_elem else ""
    
    @staticmethod
    async def extract_manufacturer(page) -> str:
        """Extract manufacturer name."""
        elem = await page.query_selector(".manufacturers .value a")
        return (await elem.inner_text()).strip() if elem else ""
    
    @staticmethod
    async def extract_image_url(page) -> str:
        """Extract part image URL."""
        image_elem = await page.query_selector("#cloudZoomImage")
        if not image_elem:
            return ""
        
        image_url = await image_elem.get_attribute("src")
        if not image_url:
            return ""
        
        if not image_url.startswith("http"):
            image_url = f"https://www.pacparts.com{image_url}"
        
        if "default-image" in image_url:
            return ""
        
        image_url = re.sub(r'_\d+(\.[^.]+)$', r'\1', image_url)
        return image_url
    
    @staticmethod
    async def extract_price(page) -> str:
        """Extract list price."""
        price_elem = (
            await page.query_selector(".price-value-217900") or
            await page.query_selector(".product-price span[class*='price-value']")
        )
        
        if not price_elem:
            return ""
        
        price_text = (await price_elem.inner_text()).strip().replace("$", "").strip()
        return "" if price_text == "Call for pricing" else price_text
    
    @staticmethod
    async def extract_availability_and_replacement(page) -> Tuple[str, str]:
        """Extract availability status and replacement part."""
        availability = "available"
        replacement = ""
        
        stock_elem = await page.query_selector(".stockquantity")
        if not stock_elem:
            return availability, replacement
        
        stock_text_normalized = " ".join((await stock_elem.inner_text()).split()).upper()
        
        if "SEE SUBSTITUTE" in stock_text_normalized:
            availability = "replaced"
            substitute_link = await page.query_selector(".stockquantity .substitute-item")
            if substitute_link:
                substitute_text = (await substitute_link.inner_text()).strip()
                replacement = substitute_text.split("CAS-")[-1].strip() if "CAS-" in substitute_text else substitute_text
        elif "DISCONTINUED" in stock_text_normalized:
            availability = "discontinued"
        elif "RESTRICTED" in stock_text_normalized:
            availability = "restricted"
        
        return availability, replacement
    
    @staticmethod
    async def extract_associated_models(page) -> Tuple[List[str], int]:
        """Extract associated models and total count."""
        model_numbers = []
        total_models = 0
        
        models_container = await page.query_selector(".associated-models-container")
        if not models_container:
            return model_numbers, total_models
        
        # Get total from footer
        footer_elem = await models_container.query_selector(".associated-models-footer")
        if footer_elem:
            footer_text = await footer_elem.inner_text()
            match = re.search(r'Total Records:\s*(\d+)', footer_text)
            if match:
                total_models = int(match.group(1))
        
        # Get all tables (handles 1 or 2 column layouts)
        all_tables = await models_container.query_selector_all(".associated-models-table")
        
        for table in all_tables:
            links = await table.query_selector_all("tbody tr td:first-child a")
            for link in links:
                model_text = (await link.inner_text()).strip()
                if model_text:
                    model_number = model_text.split()[-1]
                    model_numbers.append(model_number)
        
        return model_numbers, total_models


class PageOptimizer:
    """Handles page optimizations for faster loading."""
    
    @staticmethod
    async def setup(page):
        """Setup resource blocking for faster page loads."""
        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,webp,ico,css,woff,woff2,ttf,otf}",
            lambda route: route.abort()
        )
        await page.route(
            "**/*{google-analytics,googletagmanager,facebook,doubleclick}*/**",
            lambda route: route.abort()
        )


# ==================== Part Scraper ====================
class PartScraper:
    """Handles scraping of individual part pages."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.extractor = PartInfoExtractor()
    
    async def extract_details(self, page, url: str) -> PartDetails:
        """Extract part details from a part page with retry logic."""
        for attempt in range(self.config.retry_attempts):
            try:
                return await self._extract_details_once(page, url)
            except Exception as e:
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return PartDetails(part_url=url)
    
    async def _extract_details_once(self, page, url: str) -> PartDetails:
        """Extract part details (single attempt)."""
        await page.goto(url, wait_until="domcontentloaded", timeout=self.config.page_timeout)
        
        try:
            await page.wait_for_selector(".product-name h1", timeout=self.config.selector_timeout)
        except:
            pass
        
        # Extract all information
        part_number = await self.extractor.extract_part_number(page)
        title = await self.extractor.extract_title(page)
        manufacturer = await self.extractor.extract_manufacturer(page)
        image_url = await self.extractor.extract_image_url(page)
        price = await self.extractor.extract_price(page)
        availability, replacement = await self.extractor.extract_availability_and_replacement(page)
        model_numbers, total_models = await self.extractor.extract_associated_models(page)
        
        models_collected = len(model_numbers)
        models_match = "True" if models_collected == total_models else "False"
        
        return PartDetails(
            part_number=part_number,
            title=title,
            manufacturer=manufacturer,
            availability=availability,
            list_price=price,
            replacement=replacement,
            associated_models=",".join(model_numbers),
            part_image_url=image_url,
            part_url=url,
            total_associated_models_displayed=total_models,
            associated_models_collected=models_collected,
            associated_models_matches=models_match
        )


# ==================== CSV Handler ====================
class CSVHandler:
    """Handles CSV file operations."""
    
    @staticmethod
    def initialize_output_file(filename: str, fieldnames: List[str]) -> None:
        """Initialize output CSV file with headers."""
        if Path(filename).exists():
            Path(filename).unlink()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
    
    @staticmethod
    def load_urls(input_file: str) -> List[str]:
        """Load product URLs from CSV file (no headers)."""
        urls = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    urls.append(row[0].strip())
        return urls
    
    @staticmethod
    def append_part(part: PartDetails, output_file: str) -> None:
        """Append a single part to CSV file."""
        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PartDetails.get_fieldnames(), quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(part.to_dict())


# ==================== Worker ====================
class URLWorker:
    """Processes URLs from a queue."""
    
    def __init__(self, worker_id: int, config: ScraperConfig, 
                 scraper: PartScraper, csv_handler: CSVHandler):
        self.worker_id = worker_id
        self.config = config
        self.scraper = scraper
        self.csv_handler = csv_handler
    
    async def process_queue(self, page, url_queue: asyncio.Queue, 
                          output_file: str, counter: GlobalCounter) -> int:
        """Process URLs from a shared queue."""
        products_count = 0
        
        await PageOptimizer.setup(page)
        
        while True:
            try:
                url_index, url = await asyncio.wait_for(url_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                break
            
            try:
                part = await self.scraper.extract_details(page, url)
                self.csv_handler.append_part(part, output_file)
                
                counter.count += 1
                products_count += 1
                
                # Print progress every 10 items
                if counter.count % 10 == 0:
                    print(f"Progress: {counter.count}/{counter.total}")
                
                await asyncio.sleep(self.config.request_delay)
                
            except Exception:
                pass
            finally:
                url_queue.task_done()
        
        return products_count


# ==================== Batch Processor ====================
class BatchProcessor:
    """Processes batches of URLs with browser lifecycle management."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.scraper = PartScraper(config)
        self.csv_handler = CSVHandler()
    
    async def process_batch(self, playwright, urls_batch: List[Tuple[int, str]], 
                          batch_num: int, output_file: str, 
                          counter: GlobalCounter) -> int:
        """Process a batch of URLs with a fresh browser instance."""
        print(f"Starting Batch {batch_num} ({len(urls_batch)} URLs)")
        
        browser = await self._launch_browser(playwright)
        
        try:
            url_queue = asyncio.Queue()
            for idx, url in urls_batch:
                await url_queue.put((idx, url))
            
            pages, workers = await self._create_workers(browser)
            
            tasks = [
                workers[i].process_queue(pages[i], url_queue, output_file, counter)
                for i in range(self.config.num_workers)
            ]
            
            results = await asyncio.gather(*tasks)
            await url_queue.join()
            
            batch_total = sum(results)
            print(f"Batch {batch_num} Complete: {batch_total} parts")
            
            return batch_total
            
        finally:
            await browser.close()
    
    async def _launch_browser(self, playwright):
        """Launch browser with optimizations."""
        return await playwright.chromium.launch_persistent_context(
            user_data_dir=self.config.user_data_dir,
            channel="chrome",
            headless=self.config.headless,
            no_viewport=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-sandbox',
            ]
        )
    
    async def _create_workers(self, browser) -> Tuple[List, List]:
        """Create worker instances with their pages."""
        pages = []
        workers = []
        
        for i in range(self.config.num_workers):
            page = await browser.new_page()
            pages.append(page)
            
            worker = URLWorker(
                worker_id=i + 1,
                config=self.config,
                scraper=self.scraper,
                csv_handler=self.csv_handler
            )
            workers.append(worker)
        
        return pages, workers


# ==================== Main Orchestrator ====================
class PartDetailsScraper:
    """Main scraper orchestrator."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.csv_handler = CSVHandler()
        self.batch_processor = BatchProcessor(config)
    
    async def run(self) -> None:
        """Run the scraper."""
        if not Path(self.config.input_file).exists():
            print(f"Error: {self.config.input_file} not found!")
            return
        
        print(f"Loading URLs from {self.config.input_file}...")
        urls = self.csv_handler.load_urls(self.config.input_file)
        print(f"Found {len(urls)} URLs\n")
        
        if not urls:
            print("No URLs found")
            return
        
        self.csv_handler.initialize_output_file(
            self.config.output_file,
            PartDetails.get_fieldnames()
        )
        
        indexed_urls = list(enumerate(urls))
        num_batches = (len(urls) + self.config.batch_size - 1) // self.config.batch_size
        counter = GlobalCounter(total=len(urls))
        
        print(f"Configuration: {self.config.num_workers} workers, {num_batches} batch(es)\n")
        
        start_time = datetime.now()
        
        async with async_playwright() as p:
            try:
                batch_results = await self._process_all_batches(
                    p, indexed_urls, num_batches, counter
                )
                
                duration = datetime.now() - start_time
                
                print(f"\n{'='*60}")
                print(f"COMPLETE: {sum(batch_results)} parts")
                print(f"Time: {duration}")
                print(f"Average: {duration.total_seconds() / len(urls):.2f}s per URL")
                
                if Path(self.config.output_file).exists():
                    file_size = os.path.getsize(self.config.output_file) / (1024 * 1024)
                    print(f"File: {self.config.output_file} ({file_size:.2f} MB)")
                print(f"{'='*60}")
                
            except KeyboardInterrupt:
                print(f"\nInterrupted: {counter.count} URLs processed")
                sys.exit(0)
                
            except Exception as e:
                print(f"Error: {e}")
    
    async def _process_all_batches(self, playwright, indexed_urls, 
                                   num_batches, counter) -> List[int]:
        """Process all URL batches."""
        batch_results = []
        
        for batch_num in range(num_batches):
            start_idx = batch_num * self.config.batch_size
            end_idx = min(start_idx + self.config.batch_size, len(indexed_urls))
            batch_urls = indexed_urls[start_idx:end_idx]
            
            batch_total = await self.batch_processor.process_batch(
                playwright, batch_urls, batch_num + 1,
                self.config.output_file, counter
            )
            batch_results.append(batch_total)
            
            if batch_num < num_batches - 1:
                await asyncio.sleep(self.config.batch_pause)
        
        return batch_results


# ==================== Entry Point ====================
async def main():
    """Main entry point."""
    config = ScraperConfig()
    scraper = PartDetailsScraper(config)
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())