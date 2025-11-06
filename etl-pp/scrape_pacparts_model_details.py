import asyncio
import csv
import os
import re
import sys

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from dataclasses import dataclass

from patchright.async_api import async_playwright


# ==================== Configuration ====================
@dataclass
class ScraperConfig:
    """Configuration for the model details scraper."""
    user_data_dir: str = "./browser_profile"
    input_file: str = "casio_model_urls.csv"
    output_file: str = "casio_model_details.csv"
    num_workers: int = 3
    batch_size: int = 1000
    headless: bool = False
    retry_attempts: int = 3
    request_delay: float = 0.5
    batch_pause: int = 3
    page_timeout: int = 20000
    selector_timeout: int = 5000
    pagination_delay: float = 1.0


@dataclass
class GlobalCounter:
    """Global counter for tracking progress."""
    count: int = 0
    total: int = 0


# ==================== Data Models ====================
@dataclass
class ProductDetails:
    """Product details data model."""
    model_url: str
    model_number: str = ""
    module_number: str = ""
    manufacturer: str = ""
    type: str = ""
    category: str = ""
    year: str = ""
    model_image_url: str = ""
    total_parts_displayed: int = 0
    parts_collected: int = 0
    parts_count_matches: bool = False
    part_numbers: str = ""
    
    @classmethod
    def get_fieldnames(cls) -> List[str]:
        """Get CSV fieldnames from dataclass fields."""
        return [
            "model_url", "model_number", "module_number", "manufacturer",
            "type", "category", "year", "model_image_url",
            "total_parts_displayed", "parts_collected",
            "parts_count_matches", "part_numbers"
        ]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for CSV writing."""
        return {
            "model_url": self.model_url,
            "model_number": self.model_number,
            "module_number": self.module_number,
            "manufacturer": self.manufacturer,
            "type": self.type,
            "category": self.category,
            "year": self.year,
            "model_image_url": self.model_image_url,
            "total_parts_displayed": self.total_parts_displayed,
            "parts_collected": self.parts_collected,
            "parts_count_matches": self.parts_count_matches,
            "part_numbers": self.part_numbers
        }


# ==================== Page Extractors ====================
class PartNumberExtractor:
    """Handles extraction of part numbers from paginated tables."""
    
    @staticmethod
    async def extract_from_all_pages(page, config: ScraperConfig) -> List[str]:
        """Extract all part numbers from all pagination pages."""
        all_part_numbers = []
        
        while True:
            page_parts = await PartNumberExtractor._extract_from_current_page(page)
            all_part_numbers.extend(page_parts)
            
            if not await PartNumberExtractor._go_to_next_page(page, config):
                break
        
        return all_part_numbers
    
    @staticmethod
    async def _extract_from_current_page(page) -> List[str]:
        """Extract part numbers from current page."""
        part_rows = await page.query_selector_all("#child-grid-data tbody tr.child-grid-tr")
        part_numbers = []
        
        for row in part_rows:
            sku_elem = await row.query_selector(".child-grid-sku a")
            if sku_elem:
                sku = (await sku_elem.inner_text()).strip()
                if sku.startswith("CAS-"):
                    sku = sku[4:]
                part_numbers.append(sku)
        
        return part_numbers
    
    @staticmethod
    async def _go_to_next_page(page, config: ScraperConfig) -> bool:
        """Navigate to next page if available. Returns True if successful."""
        next_button = await page.query_selector(".dt-paging-button.next:not(.disabled)")
        if next_button:
            await next_button.click()
            await asyncio.sleep(config.pagination_delay)
            return True
        return False


class ProductInfoExtractor:
    """Extracts product information from page elements."""
    
    @staticmethod
    async def extract_model_and_module(page) -> Tuple[str, str]:
        """Extract model number and module number from product name."""
        product_name_elem = await page.query_selector(".product-name h1")
        if not product_name_elem:
            return "", ""
        
        product_name = (await product_name_elem.inner_text()).strip()
        parts = product_name.split()
        
        if not parts:
            return "", ""
        
        if len(parts) == 1:
            return parts[0].strip(), ""
        
        start_idx = 1 if parts[0].lower() == "casio" else 0
        model_number = parts[start_idx].strip() if start_idx < len(parts) else ""
        module_number = parts[-1].strip("()") if len(parts) > start_idx + 1 else ""
        
        return model_number, module_number
    
    @staticmethod
    async def extract_manufacturer(page) -> str:
        """Extract manufacturer name."""
        elem = await page.query_selector(".manufacturers .value a")
        return (await elem.inner_text()).strip() if elem else ""
    
    @staticmethod
    async def extract_type_and_category(page) -> Tuple[str, str]:
        """Extract product type and category from short description."""
        desc_elem = await page.query_selector(".short-description")
        if not desc_elem:
            return "", ""
        
        description = (await desc_elem.inner_text()).strip()
        
        if ":" in description:
            parts = description.split(":", 1)
            return parts[0].strip(), parts[1].strip()
        
        return description, description
    
    @staticmethod
    async def extract_year(page) -> str:
        """Extract year from custom field."""
        year_elem = await page.query_selector("#addField_1 .value")
        if not year_elem:
            return ""
        
        year_text = (await year_elem.inner_text()).strip()
        if not year_text:
            return ""
        
        year = year_text.split("-")[0].strip()
        return year[:4] if len(year) >= 4 else ""
    
    @staticmethod
    async def extract_image_url(page) -> str:
        """Extract product image URL."""
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
    async def extract_parts_count(page) -> int:
        """Extract total parts count from pagination info."""
        info_elem = await page.query_selector("#child-grid-data_info")
        if not info_elem:
            return 0
        
        info_text = await info_elem.inner_text()
        match = re.search(r'of (\d+) entr(?:y|ies)', info_text)
        return int(match.group(1)) if match else 0


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


# ==================== Product Scraper ====================
class ProductScraper:
    """Handles scraping of individual product pages."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.info_extractor = ProductInfoExtractor()
        self.part_extractor = PartNumberExtractor()
    
    async def extract_details(self, page, url: str) -> ProductDetails:
        """Extract product details from a product page with retry logic."""
        for attempt in range(self.config.retry_attempts):
            try:
                return await self._extract_details_once(page, url)
            except Exception as e:
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return ProductDetails(model_url=url)
    
    async def _extract_details_once(self, page, url: str) -> ProductDetails:
        """Extract product details (single attempt)."""
        await page.goto(url, wait_until="domcontentloaded", timeout=self.config.page_timeout)
        
        try:
            await page.wait_for_selector(".product-name h1", timeout=self.config.selector_timeout)
        except:
            pass
        
        model_number, module_number = await self.info_extractor.extract_model_and_module(page)
        manufacturer = await self.info_extractor.extract_manufacturer(page)
        product_type, category = await self.info_extractor.extract_type_and_category(page)
        year = await self.info_extractor.extract_year(page)
        image_url = await self.info_extractor.extract_image_url(page)
        
        part_numbers, total_parts, parts_match = await self._extract_parts_info(page)
        
        return ProductDetails(
            model_url=url,
            model_number=model_number,
            module_number=module_number,
            manufacturer=manufacturer,
            type=product_type,
            category=category,
            year=year,
            model_image_url=image_url,
            total_parts_displayed=total_parts,
            parts_collected=len(part_numbers),
            parts_count_matches=parts_match,
            part_numbers=",".join(part_numbers)
        )
    
    async def _extract_parts_info(self, page) -> Tuple[List[str], int, bool]:
        """Extract parts information including count validation."""
        parts_table = await page.query_selector("#child-grid-data tbody")
        if not parts_table:
            return [], 0, True
        
        try:
            await page.wait_for_selector("#child-grid-data_info", timeout=self.config.selector_timeout)
            await asyncio.sleep(0.5)
        except:
            pass
        
        total_parts = await self.info_extractor.extract_parts_count(page)
        part_numbers = await self.part_extractor.extract_from_all_pages(page, self.config)
        parts_match = len(part_numbers) == total_parts
        
        return part_numbers, total_parts, parts_match


# ==================== CSV Handler ====================
class CSVHandler:
    """Handles CSV file operations."""
    
    @staticmethod
    def initialize_output_file(filename: str, fieldnames: List[str]) -> None:
        """Initialize output CSV file with headers."""
        if Path(filename).exists():
            Path(filename).unlink()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
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
    def append_product(product: ProductDetails, output_file: str) -> None:
        """Append a single product to CSV file."""
        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ProductDetails.get_fieldnames())
            writer.writerow(product.to_dict())


# ==================== Worker ====================
class URLWorker:
    """Processes URLs from a queue."""
    
    def __init__(self, worker_id: int, config: ScraperConfig, 
                 scraper: ProductScraper, csv_handler: CSVHandler):
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
                product = await self.scraper.extract_details(page, url)
                self.csv_handler.append_product(product, output_file)
                
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
        self.scraper = ProductScraper(config)
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
            print(f"Batch {batch_num} Complete: {batch_total} products")
            
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
class ModelDetailsScraper:
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
            ProductDetails.get_fieldnames()
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
                print(f"COMPLETE: {sum(batch_results)} products")
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
    scraper = ModelDetailsScraper(config)
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())