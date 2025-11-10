import asyncio
import json
import csv
from datetime import datetime
from pathlib import Path
import logging
import re
from asyncio import Semaphore

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')


class LeeCountyPermitScraper:
    def __init__(self, output_file="permits_data.json", user_data_dir="./chrome_profile", max_concurrent=5):
        self.base_url = "https://aca-prod.accela.com/LEECO/Cap/CapHome.aspx?module=Permitting&TabName=Home"
        
        # Create timestamped output folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("output") / f"scrape_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set output file paths in the timestamped folder
        output_path = Path(output_file)
        stem = output_path.stem
        suffix = output_path.suffix
        
        self.output_file = self.output_dir / f"{stem}{suffix}"
        self.csv_file = self.output_dir / f"{stem}.csv"
        self.user_data_dir = Path(user_data_dir)
        self.all_permits = []
        self.max_concurrent = max_concurrent
        self.semaphore = None
        self.should_stop = False
        self.context = None
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Pre-built translation table for fast label cleaning (5x faster than chained replace)
        self.label_trans = str.maketrans({
            ' ': '_', '?': '', '/': '_', ':': '', '#': 'num',
            '(': '', ')': '', ',': '', '.': '', '-': '_'
        })
    
    def _clean_label(self, label):
        """Fast label cleaning using translate() - 5x faster than chained replace()"""
        clean = label.strip().rstrip(':?')
        clean = clean.lower().translate(self.label_trans)
        return re.sub(r'_+', '_', clean).strip('_')
    
    def _clean_key(self, text):
        """Simple key cleaning for basic fields"""
        return text.strip().lower().replace(' ', '_').replace(':', '')
    
    async def _safe_extract_text(self, element):
        """Safely extract text from element"""
        try:
            if element:
                text = await element.inner_text()
                return text.strip() if text else None
            return None
        except:
            return None
    
    async def _get_text(self, element):
        """Quick shorthand for inner_text().strip() - returns empty string on error"""
        try:
            return (await element.inner_text()).strip() if element else ""
        except:
            return ""
    
    async def _extract_contact_info_from_container(self, container):
        """Extract contact information from a container (reusable for applicant, contacts, etc)"""
        contact = {}
        try:
            first_name_elem = await container.query_selector("span.contactinfo_firstname")
            last_name_elem = await container.query_selector("span.contactinfo_lastname")
            
            if first_name_elem and last_name_elem:
                first_name = (await first_name_elem.inner_text()).strip()
                last_name = (await last_name_elem.inner_text()).strip()
                contact["name"] = f"{first_name} {last_name}".strip()
            else:
                contact["name"] = None
            
            title_elem = await container.query_selector("span.contactinfo_title")
            contact["contact_id"] = await self._safe_extract_text(title_elem)
            
            business_elem = await container.query_selector("span.contactinfo_businessname")
            contact["business_name"] = await self._safe_extract_text(business_elem)
            
            address_parts = []
            address_elem = await container.query_selector("span.contactinfo_addressline1")
            if address_elem:
                address_parts.append((await address_elem.inner_text()).strip())
            
            region_elems = await container.query_selector_all("span.contactinfo_region")
            if region_elems:
                region_texts = []
                for region_elem in region_elems:
                    region_text = (await region_elem.inner_text()).strip().rstrip(',').strip()
                    if region_text:
                        region_texts.append(region_text)
                if region_texts:
                    address_parts.append(", ".join(region_texts))
            
            contact["address"] = ", ".join(address_parts) if address_parts else None
            
            phone1_elem = await container.query_selector("span.contactinfo_phone1 div.ACA_PhoneNumberLTR")
            contact["primary_phone"] = await self._safe_extract_text(phone1_elem)
            
            phone3_elem = await container.query_selector("span.contactinfo_phone3 div.ACA_PhoneNumberLTR")
            contact["cell_phone"] = await self._safe_extract_text(phone3_elem)
            
            phone2_elem = await container.query_selector("span.contactinfo_phone2 div.ACA_PhoneNumberLTR")
            contact["alternate_phone"] = await self._safe_extract_text(phone2_elem)
            
            fax_elem = await container.query_selector("span.contactinfo_fax div.ACA_PhoneNumberLTR")
            contact["fax"] = await self._safe_extract_text(fax_elem)
            
            email_elem = await container.query_selector("span.contactinfo_email table td:last-child td")
            if not email_elem:
                email_elem = await container.query_selector("span.contactinfo_email td:not(:has(table))")
            contact["email"] = await self._safe_extract_text(email_elem)
        except:
            pass
        
        return contact
    
    async def _extract_workflow_step_details(self, item_text):
        """Extract workflow step details from text"""
        step_details = {}
        
        due_match = re.search(r'Due on\s+([0-9/]+)', item_text)
        if due_match:
            step_details["due_date"] = due_match.group(1)
        
        assigned_match = re.search(r'assigned to\s+([^,\n]+)', item_text)
        if assigned_match:
            step_details["assigned_to"] = assigned_match.group(1).strip()
        
        marked_match = re.search(r'Marked as\s+([^\n]+?)\s+on', item_text)
        if marked_match:
            step_details["marked_as"] = marked_match.group(1).strip()
        
        marked_date_match = re.search(r'on\s+([0-9/]+)\s+by', item_text)
        if marked_date_match:
            step_details["marked_date"] = marked_date_match.group(1)
        
        marked_by_match = re.search(r'by\s+([^\n]+)', item_text)
        if marked_by_match:
            step_details["marked_by"] = marked_by_match.group(1).strip()
        
        return step_details
    
    async def _extract_fee_rows_from_table(self, table):
        """Extract fee rows from a fee table"""
        fees = []
        total = None
        
        try:
            rows = await table.query_selector_all("tr.ACA_TabRow_Odd, tr.ACA_TabRow_Even")
            
            for row in rows:
                try:
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 3:
                        fee = {}
                        
                        date_div = await cells[0].query_selector("div")
                        if date_div:
                            fee["date"] = (await date_div.inner_text()).strip()
                        
                        invoice_div = await cells[1].query_selector("div")
                        if invoice_div:
                            fee["invoice_number"] = (await invoice_div.inner_text()).strip()
                        
                        amount_div = await cells[2].query_selector("div")
                        if amount_div:
                            fee["amount"] = (await amount_div.inner_text()).strip()
                        
                        if fee.get("invoice_number"):
                            fees.append(fee)
                except:
                    continue
            
            total_row = await table.query_selector("tr td[colspan]")
            if total_row:
                total_text = await total_row.inner_text()
                total_match = re.search(r'\$[\d,]+\.?\d*', total_text)
                if total_match:
                    total = total_match.group(0)
        except:
            pass
        
        return fees, total
        
    async def search_permits(self, page, start_date, end_date):
        logger.info(f"Searching permits {start_date} to {end_date}")
        
        await page.goto(self.base_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        start_date_field = "input[name='ctl00$PlaceHolderMain$generalSearchForm$txtGSStartDate']"
        await page.focus(start_date_field)
        await page.wait_for_timeout(200)
        await page.keyboard.press("Control+A")
        await page.wait_for_timeout(200)
        await page.keyboard.press("Delete")
        await page.wait_for_timeout(200)
        await page.type(start_date_field, start_date, delay=100)
        await page.wait_for_timeout(2000)
        
        end_date_field = "input[name='ctl00$PlaceHolderMain$generalSearchForm$txtGSEndDate']"
        await page.focus(end_date_field)
        await page.wait_for_timeout(200)
        await page.keyboard.press("Control+A")
        await page.wait_for_timeout(200)
        await page.keyboard.press("Delete")
        await page.wait_for_timeout(200)
        await page.type(end_date_field, end_date, delay=100)
        await page.wait_for_timeout(2000)
        
        search_button = "a#ctl00_PlaceHolderMain_btnNewSearch"
        await page.click(search_button)
        await page.wait_for_timeout(5000)
        
        try:
            await page.wait_for_selector("table.ACA_GridView", timeout=5000)
        except:
            logger.info("No results found")
            return
    
    async def extract_search_table_data(self, row):
        try:
            search_data = {}
            
            try:
                record_link = await row.query_selector("a[id*='hlPermitNumber']")
                if record_link:
                    search_data["record_number"] = (await record_link.inner_text()).strip()
                    detail_url = await record_link.get_attribute("href")
                    if detail_url and not detail_url.startswith('http'):
                        detail_url = f"https://aca-prod.accela.com{detail_url}"
                    search_data["detail_url"] = detail_url
                else:
                    record_span = await row.query_selector("span[id*='lblPermitNumber']")
                    if record_span:
                        search_data["record_number"] = (await record_span.inner_text()).strip()
                        search_data["detail_url"] = None
            except:
                search_data["record_number"] = None
                search_data["detail_url"] = None
            
            try:
                address_span = await row.query_selector("span[id*='lblAddress']")
                search_data["address"] = await self._safe_extract_text(address_span)
            except:
                search_data["address"] = None
            
            try:
                desc_span = await row.query_selector("span[id*='lblDescription']")
                search_data["description"] = await self._safe_extract_text(desc_span)
            except:
                search_data["description"] = None
            
            try:
                status_span = await row.query_selector("span[id*='lblStatus']")
                search_data["status"] = await self._safe_extract_text(status_span)
            except:
                search_data["status"] = None
            
            try:
                action_link = await row.query_selector("a[id*='btnFeeStatus']")
                search_data["action"] = await self._safe_extract_text(action_link)
            except:
                search_data["action"] = None
            
            try:
                related_div = await row.query_selector("td:nth-child(7) div.ACA_CapListStyle")
                if related_div:
                    related_text = (await related_div.inner_text()).strip()
                    search_data["related_records"] = related_text
                else:
                    search_data["related_records"] = None
            except:
                search_data["related_records"] = None
            
            try:
                submittal_span = await row.query_selector("span[id*='lblShortNote']")
                search_data["submittal_type"] = await self._safe_extract_text(submittal_span)
            except:
                search_data["submittal_type"] = None
            
            return search_data
        except Exception as e:
            logger.debug(f"Error extracting search table data: {str(e)}")
            return {}
    
    async def extract_single_permit_details(self, context, search_data, record_number):
        async with self.semaphore:
            detail_page = await context.new_page()
            try:
                detail_url = search_data["detail_url"]
                logger.info(f"[Concurrent] Extracting: {record_number}")
                
                details = await self.extract_permit_details(detail_page, detail_url, record_number)
                permit_data = {**search_data}
                
                if details:
                    for key, value in details.items():
                        if key == "record_number":
                            continue
                        elif key == "work_location":
                            if not permit_data.get("address"):
                                permit_data["address"] = value
                            permit_data["work_location"] = value
                        elif key == "record_status":
                            if not permit_data.get("status"):
                                permit_data["status"] = value
                            permit_data["record_status"] = value
                        else:
                            permit_data[key] = value
                
                logger.info(f"[Concurrent] ✓ Completed: {record_number}")
                return permit_data
            except Exception as e:
                logger.error(f"[Concurrent] Error {record_number}: {str(e)}")
                return search_data
            finally:
                await detail_page.close()
    
    async def scrape_permits_page_by_page(self, page, extract_details=False):
        page_number = 1
        total_permits_processed = 0
        processed_permit_ids = set()
        
        if self.semaphore is None:
            self.semaphore = Semaphore(self.max_concurrent)
        
        while True:
            if self.should_stop:
                logger.info("Stop requested, terminating scrape...")
                break
            logger.info(f"Processing page {page_number}")
            
            await page.wait_for_selector("table.ACA_GridView", timeout=10000)
            await page.wait_for_timeout(1000)
            
            rows = await page.query_selector_all("table.ACA_GridView tr.ACA_TabRow_Odd, table.ACA_GridView tr.ACA_TabRow_Even")
            
            if not rows:
                logger.warning(f"No rows found on page {page_number}")
                break
            
            logger.info(f"Found {len(rows)} permits on page {page_number}")
            
            page_permits = []
            for i, row in enumerate(rows, 1):
                try:
                    search_data = await self.extract_search_table_data(row)
                    
                    if not search_data or not search_data.get("record_number"):
                        continue
                    
                    record_number = search_data["record_number"]
                    
                    if record_number in processed_permit_ids:
                        continue
                    
                    processed_permit_ids.add(record_number)
                    total_permits_processed += 1
                    
                    logger.info(f"Queuing {i}/{len(rows)}: {record_number} (Total: {total_permits_processed})")
                    page_permits.append((search_data, record_number))
                except Exception as e:
                    logger.error(f"Error processing row {i}: {str(e)}")
                    continue
            
            if extract_details and page_permits:
                context = page.context
                tasks = []
                
                for search_data, record_number in page_permits:
                    if search_data.get("detail_url"):
                        task = self.extract_single_permit_details(context, search_data, record_number)
                        tasks.append(task)
                    else:
                        tasks.append(asyncio.create_task(asyncio.sleep(0, result=search_data)))
                
                logger.info(f"Processing {len(tasks)} permits concurrently (max {self.max_concurrent})")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Task failed: {result}")
                        continue
                    if result:
                        self.all_permits.append(result)
                
                self.save_to_json()
                logger.info(f"Completed page {page_number}")
            elif page_permits:
                for search_data, _ in page_permits:
                    self.all_permits.append(search_data)
                self.save_to_json()
            
            # Check if there's a next button (as clickable link, not disabled span)
            next_button = await page.query_selector("td.aca_pagination_PrevNext a:has-text('Next')")
            
            if not next_button:
                logger.info(f"Reached last page (page {page_number}) - Next button is disabled")
                break
            
            logger.info(f"Moving to page {page_number + 1}")
            
            try:
                # Use JavaScript click to trigger the ASP.NET postback
                await page.evaluate("""
                    () => {
                        const nextBtn = Array.from(document.querySelectorAll("td.aca_pagination_PrevNext a"))
                            .find(a => a.textContent.includes('Next'));
                        if (nextBtn) nextBtn.click();
                    }
                """)
                
                # Wait for the postback to start
                await page.wait_for_timeout(500)
                
                # Wait for loading mask to disappear
                try:
                    await page.wait_for_function(
                        """
                        () => {
                            const mask = document.querySelector('div#divGlobalLoadingMask');
                            return !mask || mask.classList.contains('ACA_Hide');
                        }
                        """,
                        timeout=15000
                    )
                except Exception as e:
                    logger.warning(f"Loading mask timeout: {e}")
                
                # Wait for page number to update
                next_page_number = page_number + 1
                try:
                    await page.wait_for_function(
                        f"""
                        () => {{
                            const selectedBtn = document.querySelector('span.SelectedPageButton');
                            return selectedBtn && selectedBtn.textContent.trim() === '{next_page_number}';
                        }}
                        """,
                        timeout=10000
                    )
                    logger.info(f"✓ Successfully navigated to page {next_page_number}")
                except Exception as e:
                    logger.warning(f"Page number didn't update to {next_page_number}: {e}")
                    # Try one more wait
                    await page.wait_for_timeout(2000)
                
                # Additional stabilization wait
                await page.wait_for_timeout(1500)
                
                page_number += 1
                
            except Exception as e:
                logger.error(f"Error during pagination: {str(e)}")
                break
        
        logger.info(f"Scraping complete! Total permits: {total_permits_processed} across {page_number} pages")
    
    async def navigate_to_tab(self, page, tab_name, parent_menu=None):
        try:
            if parent_menu:
                parent_selector = f'a.par-menu[data-label*="{parent_menu.lower().replace(" ", "")}"], a.par-menu:has-text("{parent_menu}")'
                try:
                    await page.click(parent_selector, timeout=3000)
                    await page.wait_for_timeout(500)
                except:
                    pass
            
            tab_selector = f'a[data-control="tab-{tab_name}"]'
            tab_element = await page.query_selector(tab_selector)
            if not tab_element:
                return False
            
            await page.click(tab_selector)
            await page.wait_for_timeout(1000)
            return True
        except:
            return False
    
    async def expand_more_details(self, page):
        try:
            more_details_link = await page.query_selector("a#lnkMoreDetail")
            if more_details_link:
                await more_details_link.click()
                await page.wait_for_timeout(1000)
            
            subsection_links = ["a#lnkRc", "a#lnkASI", "a#lnkASITableList", "a#lnkParcelList"]
            
            for link_selector in subsection_links:
                try:
                    link = await page.query_selector(link_selector)
                    if link:
                        await link.click()
                        await page.wait_for_timeout(500)
                except:
                    pass
        except:
            pass
    
    async def extract_related_contacts(self, page):
        contacts = []
        try:
            contacts_table = await page.query_selector("table#ctl00_PlaceHolderMain_PermitDetailList1_RelatContactList")
            if not contacts_table:
                return None
            
            contact_divs = await contacts_table.query_selector_all("div.MoreDetail_ItemCol1")
            
            for contact_div in contact_divs:
                try:
                    contact = await self._extract_contact_info_from_container(contact_div)
                    if contact.get("name") or contact.get("business_name"):
                        contacts.append(contact)
                except:
                    continue
        except:
            return None
        
        return contacts if contacts else None
    
    async def extract_application_information(self, page):
        app_info = {}
        try:
            app_info_div = await page.query_selector("div#ctl00_PlaceHolderMain_PermitDetailList1_phPlumbingGroup")
            if not app_info_div:
                return None
            
            full_html = await app_info_div.inner_html()
            section_pattern = r'<div class="MoreDetail_ItemTitle[^>]*>([^<]+)</div>'
            sections = re.split(section_pattern, full_html)
            current_section = None
            
            for i in range(len(sections)):
                if i == 0:
                    continue
                
                if i % 2 == 1:
                    current_section = sections[i].strip()
                    if current_section:
                        app_info[current_section] = {}
                else:
                    if current_section and current_section in app_info:
                        section_html = sections[i]
                        
                        standard_labels = re.findall(
                            r'<div class="MoreDetail_ItemColASI MoreDetail_ItemCol1"[^>]*>.*?<span class="ACA_SmLabelBolder[^>]*>([^<]+)</span>.*?</div>',
                            section_html, re.DOTALL
                        )
                        standard_values = re.findall(
                            r'<div class="MoreDetail_ItemColASI MoreDetail_ItemCol2">.*?<span class="ACA_SmLabel ACA_SmLabel_FontSize">([^<]+)</span>.*?</div>',
                            section_html, re.DOTALL
                        )
                        
                        for j, label in enumerate(standard_labels):
                            if j < len(standard_values):
                                key = self._clean_label(label)
                                app_info[current_section][key] = standard_values[j].strip()
                        
                        two_column_divs = re.findall(
                            r'<div class="ACA_FLeft ASIReview2Columns">(.*?)</div>',
                            section_html, re.DOTALL
                        )
                        
                        for column_div in two_column_divs:
                            label_match = re.search(r'<span class="ACA_SmLabelBolder"[^>]*>([^<]+)</span>', column_div)
                            value_match = re.search(r'<span class="ACA_SmLabel">([^<]+)</span>', column_div)
                            
                            if label_match and value_match:
                                key = self._clean_label(label_match.group(1))
                                app_info[current_section][key] = value_match.group(1).strip()
        except:
            return None
        
        return app_info if app_info else None
    
    async def extract_application_information_table(self, page):
        tables_data = []
        try:
            table_sections = await page.query_selector_all("tr#trASITList table[cellpadding='0'][cellspacing='0']")
            
            for table_section in table_sections:
                section_data = {}
                
                title_elem = await table_section.query_selector("div.ACA_TabRow.ACA_Title_Text")
                if title_elem:
                    section_data["section_title"] = (await title_elem.inner_text()).strip()
                
                items = []
                item_rows = await table_section.query_selector_all("tr:has(div.MoreDetail_Item)")
                
                for item_row in item_rows:
                    item_data = {}
                    labels = await item_row.query_selector_all("span.ACA_SmLabelBolder")
                    values = await item_row.query_selector_all("span.ACA_SmLabel.ACA_SmLabel_FontSize")
                    
                    for j, label_elem in enumerate(labels):
                        try:
                            label_text = (await label_elem.inner_text()).strip().rstrip(':')
                            if j < len(values):
                                value_text = (await values[j].inner_text()).strip()
                                key = self._clean_key(label_text)
                                item_data[key] = value_text
                        except:
                            continue
                    
                    if item_data:
                        items.append(item_data)
                
                if items:
                    section_data["items"] = items
                    tables_data.append(section_data)
        except:
            return None
        
        return tables_data if tables_data else None
    
    async def extract_processing_status(self, page):
        try:
            processing_table = await page.query_selector("div#divProcessingTable table")
            if not processing_table:
                return None
            
            workflows = {}
            all_rows = await processing_table.query_selector_all("tr")
            
            i = 0
            while i < len(all_rows):
                row = all_rows[i]
                try:
                    row_id = await row.get_attribute("id")
                    if row_id:
                        i += 1
                        continue
                    
                    name_cell = await row.query_selector("td.ACA_ALeft[width='770px']")
                    if not name_cell:
                        i += 1
                        continue
                    
                    workflow_name = (await name_cell.inner_text()).strip()
                    i += 1
                    
                    expand_link = await row.query_selector("a[id^='lnk_']")
                    if expand_link and i < len(all_rows):
                        detail_row = all_rows[i]
                        await expand_link.click()
                        await page.wait_for_timeout(500)
                        
                        detail_items = await detail_row.query_selector_all("tr.ACA_TabRow_Bold, tr.ACA_TabRow_Italic")
                        
                        if detail_items and len(detail_items) > 0:
                            workflow_steps = []
                            
                            for item in detail_items:
                                try:
                                    item_text = await item.inner_text()
                                    if item_text.strip():
                                        step_details = await self._extract_workflow_step_details(item_text)
                                        if step_details:
                                            workflow_steps.append(step_details)
                                except:
                                    continue
                            
                            if len(workflow_steps) == 1:
                                workflows[workflow_name] = workflow_steps[0]
                            elif len(workflow_steps) > 1:
                                workflows[workflow_name] = workflow_steps
                            else:
                                workflows[workflow_name] = None
                        else:
                            workflows[workflow_name] = None
                    else:
                        workflows[workflow_name] = None
                except:
                    pass
                
                i += 1
            
            return workflows if workflows else None
        except:
            return None
    
    async def extract_related_records(self, page):
        try:
            no_records_msg = await page.query_selector("div#divRelatedCapTree span.ACA_CapDetail_NoRecord")
            if no_records_msg:
                return None
            
            await page.wait_for_selector("table#tableCapTreeList", timeout=5000)
            related_table = await page.query_selector("table#tableCapTreeList")
            if not related_table:
                return None
            
            related_records = []
            rows = await related_table.query_selector_all("tr[name]")
            
            for idx, row in enumerate(rows, 1):
                try:
                    record = {}
                    cells = await row.query_selector_all(":scope > td")
                    
                    if len(cells) < 4:
                        continue
                    
                    try:
                        nested_table = await cells[0].query_selector("table")
                        if nested_table:
                            nested_cells = await nested_table.query_selector_all("td")
                            if len(nested_cells) >= 3:
                                record_number_text = await nested_cells[2].inner_text()
                                record_number = record_number_text.strip()
                                if record_number:
                                    record["related_record_number"] = record_number
                                else:
                                    continue
                            else:
                                continue
                        else:
                            continue
                    except:
                        continue
                    
                    try:
                        record_type_text = await cells[1].inner_text()
                        record["related_record_type"] = record_type_text.strip() if record_type_text.strip() else None
                    except:
                        record["related_record_type"] = None
                    
                    try:
                        project_name_text = await cells[2].inner_text()
                        record["related_project_name"] = project_name_text.strip() if project_name_text.strip() else None
                    except:
                        record["related_project_name"] = None
                    
                    try:
                        date_div = await cells[3].query_selector("div.ACA_NShot")
                        if date_div:
                            date_text = await date_div.inner_text()
                            record["related_date"] = date_text.strip() if date_text.strip() else None
                        else:
                            date_text = await cells[3].inner_text()
                            record["related_date"] = date_text.strip() if date_text.strip() else None
                    except:
                        record["related_date"] = None
                    
                    try:
                        if len(cells) > 4:
                            shot_div = await cells[4].query_selector("div.ACA_Shot")
                            if shot_div:
                                view_link = await shot_div.query_selector("a#detail")
                                if view_link:
                                    detail_url = await view_link.get_attribute("href")
                                    if detail_url:
                                        if not detail_url.startswith('http'):
                                            if detail_url.startswith('../'):
                                                detail_url = detail_url.replace('../', '/')
                                            detail_url = f"https://aca-prod.accela.com/LEECO{detail_url}"
                                        record["related_detail_url"] = detail_url
                                    else:
                                        record["related_detail_url"] = None
                                else:
                                    record["related_detail_url"] = None
                            else:
                                record["related_detail_url"] = None
                        else:
                            record["related_detail_url"] = None
                    except:
                        record["related_detail_url"] = None
                    
                    if record.get("related_record_number"):
                        related_records.append(record)
                except:
                    continue
            
            return related_records if related_records else None
        except:
            return None
    
    async def extract_conditions(self, page):
        conditions = []
        try:
            await page.wait_for_selector("div#divGeneralConditions", timeout=5000)
            
            conditions_table = await page.query_selector("table#ctl00_PlaceHolderMain_capConditions_gdvGeneralConditionsList")
            if not conditions_table:
                return None
            
            rows = await conditions_table.query_selector_all("tr.ACA_TabRow_Odd, tr.ACA_TabRow_Even")
            current_group = None
            
            for row in rows:
                try:
                    condition = {}
                    
                    group_name_div = await row.query_selector("div[id*='divGeneralConditionsGroupName']")
                    if group_name_div:
                        group_name_elem = await group_name_div.query_selector("span[id*='lblGeneralConditionsGroupName']")
                        if group_name_elem:
                            current_group = (await group_name_elem.inner_text()).strip()
                    
                    if current_group:
                        condition["group"] = current_group
                    
                    type_div = await row.query_selector("div[id*='divGeneralConditionsType']")
                    if type_div:
                        type_elem = await type_div.query_selector("span[id*='lblGeneralConditionsType']")
                        if type_elem:
                            condition["type"] = (await type_elem.inner_text()).strip()
                    
                    info_span = await row.query_selector("span[id*='lblGeneralConditionsInfo']")
                    if info_span:
                        info_html = await info_span.inner_html()
                        
                        title_match = re.search(r'<div[^>]*font-weight: bold[^>]*>([^<]+)</div>', info_html)
                        if title_match:
                            condition["title"] = title_match.group(1).strip()
                        
                        desc_match = re.search(r'<div[^>]*font-style: italic[^>]*>([^<]+)</div>', info_html)
                        if desc_match:
                            condition["description"] = desc_match.group(1).strip()
                        
                        status_date_match = re.search(r'<div[^>]*>([^<|]+)\|\s*(&nbsp;)?(\d{2}/\d{2}/\d{4})</div>', info_html)
                        if status_date_match:
                            condition["status"] = status_date_match.group(1).strip()
                            condition["date"] = status_date_match.group(3).strip()
                        else:
                            info_text = await info_span.inner_text()
                            status_date_text_match = re.search(r'([^|\n]+)\|\s*(\d{2}/\d{2}/\d{4})\s*$', info_text, re.MULTILINE)
                            if status_date_text_match:
                                condition["status"] = status_date_text_match.group(1).strip()
                                condition["date"] = status_date_text_match.group(2).strip()
                    
                    if condition.get("title"):
                        conditions.append(condition)
                except:
                    continue
            
            return conditions if conditions else None
        except:
            return None
    
    async def _extract_fee_section(self, page, div_selector, table_selector, fees_key, total_key):
        """Helper to extract fees from a specific section"""
        try:
            fee_div = await page.query_selector(div_selector)
            if fee_div:
                style = await fee_div.get_attribute("style")
                if not style or "display: none" not in style:
                    fee_table = await fee_div.query_selector(table_selector)
                    if fee_table:
                        fees, total = await self._extract_fee_rows_from_table(fee_table)
                        return {fees_key: fees} if fees else {}, {total_key: total} if total else {}
        except:
            pass
        return {}, {}
    
    async def extract_fees(self, page):
        fees_data = {}
        
        try:
            await page.wait_for_selector("div#divFeeListContent", timeout=5000)
            
            # Extract outstanding fees
            outstanding_fees, outstanding_total = await self._extract_fee_section(
                page,
                "div#divFeeList",
                "table#ctl00_PlaceHolderMain_FeeList_gdvFeeUnpaidList",
                "outstanding_fees",
                "total_outstanding"
            )
            fees_data.update(outstanding_fees)
            fees_data.update(outstanding_total)
            
            # Extract paid fees
            paid_fees, paid_total = await self._extract_fee_section(
                page,
                "div#divFeeListPaid",
                "table#ctl00_PlaceHolderMain_FeeList_gdvFeeUnpaidList",
                "paid_fees",
                "total_paid"
            )
            fees_data.update(paid_fees)
            fees_data.update(paid_total)
            
            return fees_data if fees_data else None
        except:
            return None
    
    async def extract_applicant_info(self, page):
        try:
            applicant_section = await page.query_selector("span[id*='per_permitDetail_label_applicant']")
            if not applicant_section:
                return None
            
            parent_container = await applicant_section.evaluate_handle("el => el.closest('td')")
            applicant = await self._extract_contact_info_from_container(parent_container)
            return applicant if applicant else None
        except:
            return None
    
    async def extract_licensed_professional_info(self, page):
        try:
            lp_table = await page.query_selector("table#tbl_licensedps")
            if not lp_table:
                return None
            
            expand_link = await page.query_selector("a#link_licenseProfessional")
            if expand_link:
                link_text = await expand_link.inner_text()
                if "View Additional" in link_text or "Show Additional" in link_text:
                    try:
                        await expand_link.click()
                        await page.wait_for_timeout(500)
                    except:
                        pass
            
            professionals = []
            all_rows = await lp_table.query_selector_all("tr")
            
            for row in all_rows:
                try:
                    row_html = await row.inner_html()
                    if not row_html or "&nbsp;" in row_html and len(row_html) < 50:
                        continue
                    if "<<Hide Additional" in row_html or "View Additional" in row_html:
                        continue
                    
                    info_cell = await row.query_selector("td:nth-child(2)")
                    if not info_cell:
                        continue
                    
                    professional = {}
                    full_text = await info_cell.inner_text()
                    if not full_text.strip():
                        continue
                    
                    all_lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    lines = [line for line in all_lines if line not in ["Primary Phone:", "Fax:", "Alternate Phone:"]]
                    
                    if len(lines) < 2:
                        continue
                    
                    professional["name"] = lines[0] if len(lines) > 0 else None
                    professional["business_name"] = lines[1] if len(lines) > 1 else None
                    
                    address_parts = []
                    if len(lines) > 2:
                        address_parts.append(lines[2])
                    if len(lines) > 3:
                        address_parts.append(lines[3])
                    
                    professional["address"] = ", ".join(address_parts) if address_parts else None
                    
                    all_phone_divs = await info_cell.query_selector_all("div.ACA_PhoneNumberLTR")
                    primary_phone = None
                    alternate_phone = None
                    fax = None
                    
                    for phone_div in all_phone_divs:
                        parent_row_elem = await phone_div.evaluate_handle("el => el.closest('tr')")
                        row_text = await parent_row_elem.inner_text()
                        phone_value = await phone_div.inner_text()
                        
                        if "Primary Phone:" in row_text:
                            primary_phone = phone_value.strip()
                        elif "Alternate Phone:" in row_text:
                            alternate_phone = phone_value.strip()
                        elif "Fax:" in row_text:
                            fax = phone_value.strip()
                    
                    professional["primary_phone"] = primary_phone
                    professional["alternate_phone"] = alternate_phone
                    professional["fax"] = fax
                    
                    license_info = None
                    license_pattern = r'\b[A-Z]{2,4}\d{5,}\b'
                    
                    for line in lines:
                        if line == professional.get("name") or line == professional.get("business_name"):
                            continue
                        if re.search(r',\s*[A-Z]{2},?\s*\d{5}', line):
                            continue
                        if re.search(license_pattern, line):
                            license_info = line.strip()
                            break
                    
                    if not license_info:
                        for line in lines:
                            line_upper = line.upper()
                            if line == professional.get("business_name"):
                                continue
                            if ('CERTIFIED' in line_upper or 'LICENSE' in line_upper or 'PRIVATE PROVIDER' in line_upper) and \
                               ('CONTRACTOR' in line_upper or 'CNTR' in line_upper or 'PP' in line_upper or 'PROVIDER' in line_upper):
                                license_info = line.strip()
                                break
                    
                    professional["license"] = license_info
                    
                    if professional.get("name") or professional.get("business_name"):
                        professionals.append(professional)
                except:
                    continue
            
            if len(professionals) == 0:
                return None
            elif len(professionals) == 1:
                return professionals[0]
            else:
                return professionals
        except:
            return None
    
    async def extract_project_description(self, page):
        try:
            project_label = await page.query_selector("span[id*='per_permitDetail_label_projectl']")
            if not project_label:
                return None
            
            parent_td = await project_label.evaluate_handle("el => el.closest('td')")
            project_table = await parent_td.query_selector("table.table_child td:last-child")
            
            if project_table:
                full_text = await project_table.inner_text()
                return full_text.strip()
            return None
        except:
            return None
    
    async def extract_work_location(self, page):
        try:
            work_location_table = await page.query_selector("table#tbl_worklocation")
            if not work_location_table:
                return None
            
            rows = await work_location_table.query_selector_all("tr")
            locations = []
            current_location = []
            
            for row in rows:
                row_text = await row.inner_text()
                row_text = row_text.strip()
                
                if not row_text:
                    continue
                    
                if '<<Hide Additional Locations' in row_text or '>>Show Additional Locations' in row_text:
                    continue
                
                if re.match(r'^\d+\)', row_text):
                    if current_location:
                        location_str = ", ".join(current_location).replace('*', '').strip()
                        if location_str:
                            locations.append(location_str)
                    current_location = [re.sub(r'^\d+\)\s*', '', row_text)]
                else:
                    if row_text:
                        current_location.append(row_text)
            
            if current_location:
                location_str = ", ".join(current_location).replace('*', '').strip()
                if location_str:
                    locations.append(location_str)
            
            if len(locations) == 0:
                return None
            elif len(locations) == 1:
                return locations[0]
            else:
                return {
                    "primary_location": locations[0],
                    "additional_locations": locations[1:]
                }
        except:
            return None
    
    async def extract_permit_details(self, page, permit_url, permit_id):
        try:
            await page.goto(permit_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            permit_data = {}
            
            try:
                permit_data["record_number"] = await page.inner_text("span#ctl00_PlaceHolderMain_lblPermitNumber")
            except:
                permit_data["record_number"] = None
            
            try:
                permit_data["permit_type"] = await page.inner_text("span#ctl00_PlaceHolderMain_lblPermitType")
            except:
                permit_data["permit_type"] = None
            
            try:
                permit_data["record_status"] = await page.inner_text("span#ctl00_PlaceHolderMain_lblRecordStatus")
            except:
                permit_data["record_status"] = None
            
            permit_data["work_location"] = await self.extract_work_location(page)
            permit_data["applicant"] = await self.extract_applicant_info(page)
            permit_data["licensed_professional"] = await self.extract_licensed_professional_info(page)
            permit_data["project_description"] = await self.extract_project_description(page)
            
            await self.expand_more_details(page)
            await page.wait_for_timeout(1000)
            
            more_details = {}
            
            related_contacts = await self.extract_related_contacts(page)
            if related_contacts:
                more_details["related_contacts"] = {"contact_information": related_contacts}
            
            app_info = await self.extract_application_information(page)
            if app_info:
                more_details["application_information"] = app_info
            
            app_info_table = await self.extract_application_information_table(page)
            if app_info_table:
                more_details["application_information_table"] = app_info_table
            
            if more_details:
                permit_data["more_details"] = more_details
            
            if await self.navigate_to_tab(page, "processing_status", parent_menu="Record Info"):
                processing_status = await self.extract_processing_status(page)
                if processing_status:
                    permit_data["processing_status"] = processing_status
            
            if await self.navigate_to_tab(page, "related_records", parent_menu="Record Info"):
                related_records_detail = await self.extract_related_records(page)
                if related_records_detail:
                    permit_data["related_records_detail"] = related_records_detail
            
            if await self.navigate_to_tab(page, "fee", parent_menu="Payments"):
                fees = await self.extract_fees(page)
                if fees:
                    permit_data["fees"] = fees
            
            if await self.navigate_to_tab(page, "conditions"):
                conditions = await self.extract_conditions(page)
                if conditions:
                    permit_data["conditions"] = conditions
            
            return permit_data
        except Exception as e:
            logger.error(f"Error extracting {permit_id}: {str(e)}")
            return None
    
    def _clean_csv_value(self, value):
        """Clean value for CSV by removing newlines and extra spaces"""
        if value is None:
            return None
        if isinstance(value, str):
            # Replace newlines with space and clean up multiple spaces
            value = value.replace('\n', ' ').replace('\r', ' ')
            value = ' '.join(value.split())  # Remove extra whitespace
        return value
    
    def _flatten_permit_for_csv(self, permit):
        """Extract most important fields from permit data for CSV export"""
        row = {
            # Basic info
            'record_number': self._clean_csv_value(permit.get('record_number')),
            'permit_type': self._clean_csv_value(permit.get('permit_type')),
            'status': self._clean_csv_value(permit.get('status')),
            'record_status': self._clean_csv_value(permit.get('record_status')),
            'description': self._clean_csv_value(permit.get('description')),
            'submittal_type': self._clean_csv_value(permit.get('submittal_type')),
            'action': self._clean_csv_value(permit.get('action')),
            'related_records': self._clean_csv_value(permit.get('related_records')),
            
            # Location
            'address': self._clean_csv_value(permit.get('address')),
            'work_location': self._clean_csv_value(permit.get('work_location')) if isinstance(permit.get('work_location'), str) else None,
            
            # Applicant info
            'applicant_name': None,
            'applicant_business': None,
            'applicant_address': None,
            'applicant_phone': None,
            'applicant_cell': None,
            'applicant_email': None,
            
            # Licensed Professional
            'licensed_professional_name': None,
            'licensed_professional_business': None,
            'licensed_professional_address': None,
            'licensed_professional_license': None,
            'licensed_professional_phone': None,
            
            # Project
            'project_description': self._clean_csv_value(permit.get('project_description')),
            'job_value': None,
            'commercial_residential': None,
            'type_of_use': None,
            'work_area_sqft': None,
            'property_use_type': None,
            'master_plan_num': None,
            
            # Fees
            'total_outstanding': None,
            'total_paid': None,
            'total_fees': None,
            
            # Status tracking
            'conditions_count': None,
            'current_workflow_step': None,
            'permit_issued_date': None,
            'application_date': None,
            
            # Link
            'detail_url': self._clean_csv_value(permit.get('detail_url'))
        }
        
        # Extract applicant details
        applicant = permit.get('applicant', {})
        if applicant:
            row['applicant_name'] = self._clean_csv_value(applicant.get('name'))
            row['applicant_business'] = self._clean_csv_value(applicant.get('business_name'))
            row['applicant_address'] = self._clean_csv_value(applicant.get('address'))
            row['applicant_phone'] = self._clean_csv_value(applicant.get('primary_phone'))
            row['applicant_cell'] = self._clean_csv_value(applicant.get('cell_phone'))
            row['applicant_email'] = self._clean_csv_value(applicant.get('email'))
        
        # Extract licensed professional details
        lp = permit.get('licensed_professional')
        if lp:
            # Handle both dict and list (take first if list)
            lp_data = lp[0] if isinstance(lp, list) and len(lp) > 0 else lp if isinstance(lp, dict) else None
            if lp_data:
                row['licensed_professional_name'] = self._clean_csv_value(lp_data.get('name'))
                row['licensed_professional_business'] = self._clean_csv_value(lp_data.get('business_name'))
                row['licensed_professional_address'] = self._clean_csv_value(lp_data.get('address'))
                row['licensed_professional_license'] = self._clean_csv_value(lp_data.get('license'))
                row['licensed_professional_phone'] = self._clean_csv_value(lp_data.get('primary_phone'))
        
        # Extract fee totals
        fees = permit.get('fees', {})
        if fees:
            row['total_outstanding'] = fees.get('total_outstanding')
            row['total_paid'] = fees.get('total_paid')
            # Calculate total fees if both values exist
            try:
                outstanding = fees.get('total_outstanding', '').replace('$', '').replace(',', '') if fees.get('total_outstanding') else '0'
                paid = fees.get('total_paid', '').replace('$', '').replace(',', '') if fees.get('total_paid') else '0'
                if outstanding or paid:
                    total = float(outstanding or 0) + float(paid or 0)
                    row['total_fees'] = f"${total:,.2f}" if total > 0 else None
            except (ValueError, AttributeError):
                pass
        
        # Extract application information from more_details
        more_details = permit.get('more_details', {})
        if more_details:
            # Application information (job value, type, etc.)
            app_info = more_details.get('application_information', {})
            if app_info:
                # Define field mappings to reduce redundant checks
                field_mappings = {
                    'job_value': ['est_const_value', 'job_value'],
                    'commercial_residential': ['commercial_residential'],
                    'type_of_use': ['type_of_use'],
                    'work_area_sqft': ['work_area_square_feet', 'plumbing_working_area_sq_ft', 'working_area_sq_ft'],
                    'property_use_type': ['property_use_type'],
                    'master_plan_num': ['master_num', 'master_plan']
                }
                
                # Look through all sections for relevant fields
                for section_name, section_data in app_info.items():
                    if isinstance(section_data, dict):
                        for row_key, source_keys in field_mappings.items():
                            if not row[row_key]:  # Only fill if not already set
                                for source_key in source_keys:
                                    value = section_data.get(source_key)
                                    if value:
                                        row[row_key] = self._clean_csv_value(value)
                                        break
        
        # Count conditions
        conditions = permit.get('conditions', [])
        if conditions:
            row['conditions_count'] = len(conditions)
        
        # Get current workflow step and key dates
        processing_status = permit.get('processing_status', {})
        if processing_status:
            # Get permit issued date
            permit_issuance = processing_status.get('Permit Issuance')
            if permit_issuance:
                if isinstance(permit_issuance, dict) and permit_issuance.get('marked_as') == 'Issued':
                    row['permit_issued_date'] = self._clean_csv_value(permit_issuance.get('marked_date'))
                elif isinstance(permit_issuance, list) and len(permit_issuance) > 0:
                    for item in permit_issuance:
                        if isinstance(item, dict) and item.get('marked_as') == 'Issued':
                            row['permit_issued_date'] = self._clean_csv_value(item.get('marked_date'))
                            break
            
            # Get application date (first date in Application step)
            application = processing_status.get('Application')
            if application and isinstance(application, list) and len(application) > 0:
                # Get the earliest marked_date as application date
                dates = [item.get('marked_date') for item in application if isinstance(item, dict) and item.get('marked_date')]
                if dates:
                    row['application_date'] = self._clean_csv_value(min(dates))
            
            # Get current workflow step (find the first in-progress or TBD step)
            for step_name, step_data in processing_status.items():
                if step_data and isinstance(step_data, list) and len(step_data) > 0:
                    # Check if any step is marked as "TBD" or in progress
                    for item in step_data:
                        if isinstance(item, dict) and item.get('marked_as') in ['TBD', 'In Progress', 'Pending']:
                            row['current_workflow_step'] = self._clean_csv_value(step_name)
                            break
                    if row['current_workflow_step']:
                        break
        
        return row
    
    def save_to_csv(self):
        """Save important permit fields to CSV"""
        try:
            if not self.all_permits:
                logger.warning("No permits to save to CSV")
                return
            
            # Define CSV columns
            csv_columns = [
                'record_number', 'permit_type', 'status', 'record_status', 
                'description', 'submittal_type', 'action', 'related_records',
                'address', 'work_location',
                'applicant_name', 'applicant_business', 'applicant_address', 
                'applicant_phone', 'applicant_cell', 'applicant_email',
                'licensed_professional_name', 'licensed_professional_business', 'licensed_professional_address', 
                'licensed_professional_license', 'licensed_professional_phone',
                'project_description', 'job_value', 'commercial_residential', 'type_of_use',
                'work_area_sqft', 'property_use_type', 'master_plan_num',
                'total_outstanding', 'total_paid', 'total_fees',
                'conditions_count', 'current_workflow_step', 'permit_issued_date', 'application_date',
                'detail_url'
            ]
            
            with open(self.csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=csv_columns, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                
                for permit in self.all_permits:
                    row = self._flatten_permit_for_csv(permit)
                    writer.writerow(row)
            
            logger.info(f"Saved {len(self.all_permits)} permits to CSV: {self.csv_file}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
    
    def save_to_json(self):
        """Save all permit data to JSON"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_permits, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.all_permits)} permits to JSON: {self.output_file}")
            
            # Also save important fields to CSV
            self.save_to_csv()
            
            # Log the output directory
            logger.info(f"All files saved to folder: {self.output_dir}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")
    
    async def run(self, start_date, end_date, extract_details=False, headless=False):
        async with async_playwright() as p:
            try:
                self.context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    channel="chrome",
                    headless=headless,
                    no_viewport=True,
                )
                
                page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                await self.search_permits(page, start_date, end_date)
                await self.scrape_permits_page_by_page(page, extract_details)
            finally:
                # Always close the context properly
                if self.context:
                    try:
                        await self.context.close()
                        logger.info("Browser context closed successfully")
                    except Exception as e:
                        logger.warning(f"Error closing context: {e}")
                    self.context = None
                
                # Save data even if stopped
                if self.all_permits:
                    logger.info(f"Saving {len(self.all_permits)} permits collected so far...")
                    self.save_to_json()
            
            # Print completion summary
            print(f"\n{'='*50}")
            status_msg = "Scraping complete!" if not self.should_stop else "Scraping stopped!"
            print(f"{status_msg} Total permits: {len(self.all_permits)}")
            print(f"Output folder: {self.output_dir}")
            print(f"  - JSON (all data): {self.output_file.name}")
            print(f"  - CSV (key fields): {self.csv_file.name}")
            print(f"{'='*50}\n")
            
            return self.all_permits


async def main():
    scraper = LeeCountyPermitScraper(
        output_file="permits_data.json",
        user_data_dir="./chrome_profile",
        max_concurrent=5
    )
    
    start_date = "11/06/2025"
    end_date = datetime.now().strftime("%m/%d/%Y")
    
    await scraper.run(start_date, end_date, extract_details=True)


if __name__ == "__main__":
    asyncio.run(main())