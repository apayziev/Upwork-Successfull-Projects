import csv
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from botasaurus.browser import browser, Driver
import us

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndeedSkillFilter:
    """Handles Indeed construction skill filtering with Botasaurus"""
    
    def __init__(self, 
                 driver,
                 output_dir: str = None,
                 file_prefix: str = None):
        self.driver = driver
        
        # Configuration
        self.base_url = "https://www.indeed.com"
        self.search_params = {
            "q": "construction",
            "l": "",
            "from": "searchOnHP,whatautocomplete,whatautocompleteSourceStandard"
        }
        
        # Dynamic output directory with timestamp if not specified
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            search_term = self.search_params.get("q", "jobs").replace(" ", "_")
            output_dir = f"indeed_{search_term}_{timestamp}"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Configurable file prefix
        self.file_prefix = file_prefix or self.search_params.get("q", "jobs")
        
        # Deduplication tracking - only by job_id (Indeed's unique identifier)
        self.processed_job_ids = set()
        
        # Track current skill being processed (for Cloudflare recovery)
        self.current_skill = None
    
    def check_and_bypass_cloudflare(self) -> bool:
        """
        Check if Cloudflare challenge is present and bypass it.
        This can be called at any time during scraping.
        r
        Returns:
            True if Cloudflare was detected and bypassed, False otherwise
        """
        try:
            # Check for Cloudflare challenge indicators
            is_cloudflare = self.driver.run_js("""
                // Check for common Cloudflare challenge indicators
                const title = document.title.toLowerCase();
                const body = document.body ? document.body.innerText.toLowerCase() : '';
                const html = document.documentElement.outerHTML.toLowerCase();
                
                // Check for Cloudflare challenge page titles
                if (title.includes('just a moment') || 
                    title.includes('attention required') ||
                    title.includes('additional verification') ||
                    title.includes('verification required') ||
                    title.includes('cloudflare')) {
                    return true;
                }
                
                // Check for Cloudflare text indicators
                if (body.includes('checking your browser') ||
                    body.includes('verify you are human') ||
                    body.includes('verifying you are human') ||
                    body.includes('ray id') ||
                    body.includes('cloudflare') ||
                    body.includes('troubleshooting cloudflare')) {
                    return true;
                }
                
                // Check for Cloudflare elements
                if (document.querySelector('#challenge-running') ||
                    document.querySelector('.cf-browser-verification') ||
                    document.querySelector('#cf-wrapper') ||
                    document.querySelector('#cf-challenge-running') ||
                    document.querySelector('iframe[src*="cloudflare"]') ||
                    document.querySelector('iframe[src*="challenges.cloudflare"]') ||
                    document.querySelector('iframe[src*="turnstile"]') ||
                    document.querySelector('[class*="cloudflare"]')) {
                    return true;
                }
                
                // Check HTML source for Cloudflare meta tags or scripts
                if (html.includes('cloudflare') && 
                    (html.includes('challenge') || html.includes('turnstile'))) {
                    return true;
                }
                
                return false;
            """)
            
            if is_cloudflare:
                logger.warning("Cloudflare detected - bypassing...")
                current_url = self.driver.current_url
                was_processing_skill = self.current_skill is not None
                
                # Use Botasaurus's built-in Cloudflare bypass
                self.driver.google_get(current_url, bypass_cloudflare=True)
                time.sleep(5)
                
                # Verify bypass was successful
                still_cloudflare = self.driver.run_js("""
                    const title = document.title.toLowerCase();
                    return title.includes('cloudflare') || title.includes('just a moment');
                """)
                
                if still_cloudflare:
                    logger.warning("Retry bypass...")
                    self.driver.google_get(current_url, bypass_cloudflare=True)
                    time.sleep(5)
                
                logger.info("Cloudflare bypassed")
                
                # If we were processing a skill, reapply the filter to continue where we left off
                if was_processing_skill:
                    logger.info(f"Reapplying filter for skill: {self.current_skill}")
                    try:
                        self.filter_by_skill(self.current_skill)
                        logger.info("Filter reapplied - continuing extraction")
                    except Exception as e:
                        logger.error(f"Failed to reapply filter: {e}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Cloudflare check failed: {e}")
            return False
    
    def navigate_to_jobs(self):
        """Navigate to Indeed jobs page with search parameters"""
        params_str = "&".join([f"{k}={v}" for k, v in self.search_params.items()])
        url = f"{self.base_url}/jobs?{params_str}"
        
        logger.info("Loading Indeed jobs page...")
        self.driver.google_get(url, bypass_cloudflare=True)
        time.sleep(5)
        
        # Wait for job cards to load
        try:
            self.driver.wait_for_element("[data-jk]")
            logger.info("Page loaded")
        except Exception as e:
            logger.warning(f"Checking for Cloudflare: {e}")
            self.check_and_bypass_cloudflare()
        
        time.sleep(3)
    
    def open_construction_skill_filter(self):
        """Click the Construction skill dropdown button"""
        button_selector = "#filter-taxo4"
        
        try:
            self.driver.scroll_into_view(button_selector)
            time.sleep(0.5)
            
            button = self.driver.select(button_selector, wait=True)
            if not button:
                raise Exception("Skill filter button not found")
            
            logger.info("Opening skill filter...")
            button.click()
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to open skill filter: {e}")
            raise
    
    def clear_all_selections(self):
        """Click the Clear all button to reset selections"""
        try:
            # Use JavaScript to find and click "Clear all" button
            result = self.driver.run_js("""
                const buttons = document.querySelectorAll('button');
                for (const button of buttons) {
                    if (button.textContent.includes('Clear all')) {
                        button.click();
                        return true;
                    }
                }
                return false;
            """)
            if result:
                logger.debug("Cleared all selections")
                time.sleep(0.5)
        except Exception:
            logger.debug("Clear all button not found or not needed")
            pass
    
    def select_skill(self, skill_name: str):
        """Select a specific skill from the dropdown"""
        time.sleep(1)
        
        # Use JavaScript to find and click the checkbox
        result = self.driver.run_js(f"""
            const labels = document.querySelectorAll('label[for^="filter-taxo4-"]');
            for (const label of labels) {{
                const textSpan = label.querySelector('span');
                if (textSpan && textSpan.innerText.trim() === '{skill_name}') {{
                    const checkbox = label.querySelector('input[type="checkbox"]');
                    if (checkbox && !checkbox.checked) {{
                        checkbox.click();
                        return true;
                    }}
                    return checkbox ? checkbox.checked : false;
                }}
            }}
            return false;
        """)
        
        if result:
            logger.info(f"Selected: {skill_name}")
            time.sleep(0.5)
        else:
            raise Exception(f"Skill '{skill_name}' not found")
    
    def apply_filter(self):
        """Click the Update button to apply the filter"""
        # Use JavaScript to find and click the Update button
        result = self.driver.run_js("""
            const updateButton = document.querySelector('button[type="submit"][form="filter-taxo4-menu"]');
            if (updateButton) {
                updateButton.click();
                return true;
            }
            return false;
        """)
        
        if not result:
            raise Exception("Update button not found")
        
        logger.info("Filter applied")
        time.sleep(3)
    
    def filter_by_skill(self, skill: str):
        """Complete workflow to filter jobs by a single construction skill"""
        self.open_construction_skill_filter()
        self.clear_all_selections()
        self.select_skill(skill)
        self.apply_filter()
    
    def get_available_skills(self) -> List[str]:
        """Get list of all available construction skills in their modal order"""
        self.open_construction_skill_filter()
        time.sleep(2)
        
        # Check if labels exist
        try:
            self.driver.select("label[for^='filter-taxo4-']", wait=True)
        except Exception as e:
            logger.error(f"Skill labels not found: {e}")
            raise
        
        time.sleep(1)
        
        skills = self.driver.run_js("""
            const skillLabels = document.querySelectorAll('label[for^="filter-taxo4-"]');
            const skills = [];
            
            skillLabels.forEach(label => {
                const input = label.querySelector('input[type="checkbox"]');
                const textSpan = label.querySelector('span.css-1br6eau, span[class*="e1excnjx0"]');
                
                if (input && textSpan) {
                    const index = input.getAttribute('data-index');
                    const skillName = textSpan.innerText.trim();
                    
                    skills.push({
                        index: parseInt(index),
                        name: skillName,
                        id: input.id
                    });
                }
            });
            
            skills.sort((a, b) => a.index - b.index);
            
            return skills.map(s => s.name);
        """)
        
        # Close modal by pressing Escape using JavaScript
        self.driver.run_js("""
            const escEvent = new KeyboardEvent('keydown', {
                key: 'Escape',
                code: 'Escape',
                keyCode: 27,
                which: 27,
                bubbles: true
            });
            document.dispatchEvent(escEvent);
        """)
        time.sleep(1)
        
        logger.info(f"Found {len(skills)} skills")
        return skills
    

    
    def parse_location(self, location_text: str) -> Dict[str, str]:
        """Parse location string to extract city, state, postal code, and street address"""
        location_info = {
            'city': '',
            'state': '',
            'postal_code': '',
            'street_address': ''
        }
        
        if not location_text:
            return location_info
        
        location_text = location_text.strip()
        original_text = location_text
        
        street_indicators = r'\b(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct|place|pl|circle|cir|parkway|pkwy)\b'
        
        # Extract postal code
        postal_matches = list(re.finditer(r'\b(\d{5}(?:-\d{4})?)\b', location_text))
        
        for match in postal_matches:
            postal_candidate = match.group(1)
            
            if match.start() == 0 or (match.start() <= 10 and location_text[:match.start()].strip() == ''):
                continue
                
            after_match = location_text[match.end():].strip()
            if after_match and re.match(r'^[A-Za-z\s]+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct|place|pl)', after_match, re.IGNORECASE):
                continue
                
            location_info['postal_code'] = postal_candidate
            location_text = location_text.replace(match.group(0), '').strip()
            break
        
        # Extract state using 'us' package for validation
        state_matches = re.finditer(r'\b([A-Z]{2})\b', location_text, re.IGNORECASE)
        
        for match in state_matches:
            potential_state = match.group(1).upper()
            # Use 'us' package to validate state abbreviation
            if us.states.lookup(potential_state):
                start_pos = max(0, match.start() - 20)
                end_pos = min(len(location_text), match.end() + 5)
                context = location_text[start_pos:end_pos].lower()
                
                if not re.search(r'\b\d+.*' + street_indicators.replace(r'\b', ''), context):
                    location_info['state'] = potential_state
                    location_text = location_text.replace(match.group(0), '').strip()
                    break
        
        location_text = re.sub(r'[,\s]+$', '', location_text)
        location_text = re.sub(r'^[,\s]+', '', location_text)
        
        parts = [part.strip() for part in location_text.split(',') if part.strip()]
        
        if len(parts) >= 2:
            first_part = parts[0]
            if (re.search(r'^\d+', first_part) and  
                (re.search(street_indicators, first_part, re.IGNORECASE) or  
                 len(first_part.split()) >= 3)):
                
                location_info['street_address'] = first_part.strip()
                
                if len(parts) > 1:
                    location_info['city'] = parts[1].strip()
                    
            else:
                location_info['city'] = first_part.strip()
                
        elif len(parts) == 1:
            single_part = parts[0].strip()
            
            if (re.search(r'^\d+', single_part) and 
                (re.search(street_indicators, single_part, re.IGNORECASE) or len(single_part.split()) >= 3)):
                location_info['street_address'] = single_part
            else:
                location_info['city'] = single_part
        
        if not location_info['city'] and location_info['state']:
            state_pattern = r'\b' + re.escape(location_info['state']) + r'\b'
            before_state_parts = re.split(state_pattern, original_text, flags=re.IGNORECASE)
            
            if len(before_state_parts) > 0:
                before_state = before_state_parts[0].strip()
                
                if location_info['postal_code']:
                    before_state = before_state.replace(location_info['postal_code'], '').strip()
                
                before_parts = [p.strip() for p in before_state.split(',') if p.strip()]
                if before_parts:
                    last_part = before_parts[-1].strip()
                    
                    if not (re.search(r'^\d+', last_part) and re.search(street_indicators, last_part, re.IGNORECASE)):
                        location_info['city'] = last_part
        
        return location_info
    
    def extract_job_cards(self) -> List[Dict[str, str]]:
        """Extract basic job information from job cards"""
        jobs = self.driver.run_js("""
            const jobCards = document.querySelectorAll('[data-jk]');
            const jobs = [];
            const seenIds = new Set();
            
            jobCards.forEach(card => {
                const jobId = card.getAttribute('data-jk');
                if (jobId && !seenIds.has(jobId)) {
                    seenIds.add(jobId);
                    jobs.push({
                        job_id: jobId,
                        card_element_id: `job_${jobId}`
                    });
                }
            });
            
            return jobs;
        """)
        
        # Only check for Cloudflare if we got 0 job cards
        if len(jobs) == 0:
            logger.warning("No jobs found - checking Cloudflare...")
            self.check_and_bypass_cloudflare()
            # Try again after bypass
            jobs = self.driver.run_js("""
                const jobCards = document.querySelectorAll('[data-jk]');
                const jobs = [];
                const seenIds = new Set();
                
                jobCards.forEach(card => {
                    const jobId = card.getAttribute('data-jk');
                    if (jobId && !seenIds.has(jobId)) {
                        seenIds.add(jobId);
                        jobs.push({
                            job_id: jobId,
                            card_element_id: `job_${jobId}`
                        });
                    }
                });
                
                return jobs;
            """)
        
        logger.info(f"Found {len(jobs)} jobs")
        return jobs
    
    def extract_detailed_job_info(self, job_id: str) -> Dict[str, str]:
        """Click on job card and extract detailed information"""
        try:
            job_link_selector = f"[data-jk='{job_id}']"
            
            # Scroll into view
            try:
                self.driver.run_js(f'''
                    const element = document.querySelector("[data-jk='{job_id}']");
                    if (element) {{
                        element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}
                ''')
                time.sleep(1)
            except:
                pass
            
            # Click with JavaScript
            try:
                self.driver.run_js(f'''
                    const element = document.querySelector("[data-jk='{job_id}']");
                    if (element) {{
                        element.addEventListener('click', (e) => e.preventDefault());
                        const event = new MouseEvent('click', {{ bubbles: true, cancelable: true }});
                        element.dispatchEvent(event);
                    }}
                ''')
                time.sleep(1)
            except Exception as click_error:
                logger.warning(f"JavaScript click failed for {job_id}: {click_error}")
                try:
                    current_url = self.driver.current_url
                    element = self.driver.select(job_link_selector)
                    element.click()
                    
                    if self.driver.current_url != current_url:
                        logger.info("Navigated away, returning to search results")
                        self.driver.back()
                        time.sleep(2)
                        return self.create_empty_job_details(job_id)
                        
                except Exception as direct_click_error:
                    logger.warning(f"Direct click also failed for {job_id}: {direct_click_error}")
                    return self.create_empty_job_details(job_id)
            
            # Wait for right pane to load
            try:
                self.driver.wait_for_element('.jobsearch-RightPane, .jobsearch-JobComponent, #jobsearch-ViewjobPaneWrapper')
            except:
                logger.warning(f"Right pane not loaded for {job_id}")
                return self.create_empty_job_details(job_id)
            
            time.sleep(1)
            
            # Extract job details
            job_details = self.create_empty_job_details(job_id)
            
            # Extract job title using JavaScript
            try:
                title_text = self.driver.run_js('''
                    const titleEl = document.querySelector('h2[data-testid="jobsearch-JobInfoHeader-title"], .jobsearch-JobInfoHeader-title');
                    if (titleEl) {
                        const mainSpan = titleEl.querySelector('span');
                            if (mainSpan) {
                                let text = '';
                                for (const node of mainSpan.childNodes) {
                                    if (node.nodeType === Node.TEXT_NODE) {
                                        text += node.textContent;
                                    }
                                }
                                return text.trim();y
                            }
                        return titleEl.textContent.trim();
                        }
                    return '';
                ''')
                    
                if title_text:
                    job_details['job_title'] = title_text.strip()
            except Exception as e:
                logger.debug(f"[SELECTOR FAILED] Job title extraction failed: {e}")
                pass
            
            # Extract employer name using JavaScript
            try:
                employer_name = self.driver.run_js('''
                    const companyEl = document.querySelector('[data-testid="inlineHeader-companyName"] a, [data-testid="inlineHeader-companyName"]');
                    return companyEl ? companyEl.innerText.trim() : '';
                ''')
                
                if employer_name:
                    job_details['employer_name'] = employer_name
            except Exception as e:
                logger.debug(f"[SELECTOR FAILED] Employer name extraction failed: {e}")
                pass
            
            # Extract location
            try:
                location_text = self.extract_location()
                if location_text:
                    parsed_location = self.parse_location(location_text)
                    job_details.update(parsed_location)
            except Exception as location_error:
                logger.warning(f"Location extraction error: {location_error}")
            
            # Extract salary and job type using JavaScript
            try:
                salary_jobtype_data = self.driver.run_js('''
                    const container = document.querySelector('#salaryInfoAndJobType');
                    if (!container) return { salary: '', jobType: '' };
                    
                    // Extract salary
                    const salaryEl = container.querySelector('.css-1oc7tea');
                    const salary = salaryEl ? salaryEl.innerText.trim() : '';
                    
                    // Extract job type
                    const jobTypeEl = container.querySelector('.css-1u1g3ig');
                    const jobType = jobTypeEl ? jobTypeEl.innerText.trim() : '';
                    
                    return { salary, jobType };
                ''')
                
                if salary_jobtype_data:
                    if salary_jobtype_data.get('salary'):
                        job_details['salary'] = salary_jobtype_data['salary']
                    
                    if salary_jobtype_data.get('jobType'):
                        # Clean up the text - remove leading/trailing whitespace, dashes, and extra spaces
                        # Handle patterns like " -  Full-time" or "Full-time" or " -  Part-time, Full-time"
                        cleaned_job_type = re.sub(r'^[\s\-]+', '', salary_jobtype_data['jobType'])
                        cleaned_job_type = cleaned_job_type.strip()
                        if cleaned_job_type:
                            job_details['job_type'] = cleaned_job_type
            except Exception as e:
                logger.debug(f"Salary/Job type extraction error: {e}")
            
            # Extract job description
            try:
                description_text = self.extract_description()
                if description_text:
                    job_details['description'] = description_text
            except Exception as description_error:
                logger.warning(f"Description extraction error: {description_error}")
            
            return job_details
            
        except Exception as e:
            logger.error(f"Error extracting detailed job info for {job_id}: {e}")
            return self.create_empty_job_details(job_id)
    
    def extract_location(self) -> str:
        """Extract location information from page using JavaScript"""
        try:
            location_text = self.driver.run_js(r'''
                const locationDivs = document.querySelectorAll('[data-testid="inlineHeader-companyLocation"] > div');
                const excludeWords = ['apply', 'button', 'click', 'save', 'report'];
                
                for (const div of locationDivs) {
                    const text = div.innerText.trim();
                    if (text && text.length > 2) {
                        // Check if it has alphabetic characters and not just digits
                        const hasAlpha = /[a-zA-Z]/.test(text);
                        const isOnlyDigits = /^\d+$/.test(text);
                        
                        // Check if it doesn't contain excluded words
                        const hasExcludedWord = excludeWords.some(word => 
                            text.toLowerCase().includes(word)
                        );
                        
                        if (hasAlpha && !isOnlyDigits && !hasExcludedWord) {
                            return text;
                        }
                    }
                }
                return '';
            ''')
            
            return location_text if location_text else ''
        except Exception as e:
            logger.debug(f"Location extraction failed: {e}")
            return ''
    
    def extract_description(self) -> str:
        """Extract and sanitize job description text using JavaScript"""
        try:
            description_text = self.driver.run_js('''
                const descEl = document.querySelector('#jobDescriptionText');
                return descEl ? descEl.innerText.trim() : '';
            ''')
            
            if description_text and description_text.strip():
                # Sanitize the description
                sanitized = description_text.strip()
                # Remove excessive whitespace and newlines
                sanitized = re.sub(r'\n\s*\n\s*\n+', '\n\n', sanitized)
                # Remove leading/trailing whitespace from each line
                sanitized = '\n'.join(line.strip() for line in sanitized.split('\n'))
                return sanitized
        except Exception as e:
            logger.debug(f"Description extraction failed: {e}")
        
        return ''
    
    def create_empty_job_details(self, job_id: str) -> Dict[str, str]:
        """Create empty job details structure"""
        return {
            'job_title': '',
            'employer_name': '',
            'city': '',
            'state': '',
            'postal_code': '',
            'street_address': '',
            'salary': '',
            'job_type': '',
            'description': '',
            'job_url': f"{self.base_url}/viewjob?jk={job_id}",
            'scraped_at': datetime.now().isoformat()
        }
    
    def generate_filename(self) -> Path:
        """Generate filename for CSV output
        
        Returns:
            Path object with generated filename
        """
        filename = f"{self.file_prefix}_all_jobs.csv"
        return self.output_dir / filename
    
    def save_to_csv(self, jobs: List[Dict[str, str]], skill: str):
        """Save job data to single CSV file
        
        Args:
            jobs: List of job dictionaries to save
            skill: Skill name (used for logging only)
        """
        if not jobs:
            logger.warning(f"No jobs to save for skill: {skill}")
            return
            
        filename = self.generate_filename()
        
        # Field names without job_id
        fieldnames = ['job_title', 'employer_name', 'city', 'state', 'postal_code', 
                     'street_address', 'salary', 'job_type', 'description', 'job_url', 'scraped_at']
        
        # Check if file exists to determine if we need to write header
        file_exists = filename.exists()
        mode = 'a' if file_exists else 'w'
        
        with open(filename, mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            
            # Write header only if file doesn't exist
            if not file_exists:
                writer.writeheader()
                
            writer.writerows(jobs)
            
        action = "Appended to" if file_exists else "Created"
        logger.info(f"{action} {filename.name}: added {len(jobs)} jobs from skill '{skill}'")
    
    def get_next_page_url(self, current_page: int) -> Optional[str]:
        """Extract next page URL from pagination - returns None when on last page"""
        next_url = self.driver.run_js(r"""
            // The ONLY reliable indicator of next page is the "Next Page" button
            const nextLink = document.querySelector('a[data-testid="pagination-page-next"]');
            if (nextLink && nextLink.href) {
                return nextLink.href;
            }
            
            // No "Next Page" button = we're on the last page
            return null;
        """)
        
        if next_url:
            return next_url
        else:
            logger.info(f"Last page reached (page {current_page})")
            return None
    
    def extract_jobs_for_skill(self, skill: str) -> int:
        """Extract all jobs for a given skill across all available pages
        
        Returns:
            Total number of jobs extracted
        """
        # Set current skill for Cloudflare recovery
        self.current_skill = skill
        
        total_jobs_extracted = 0
        page_num = 1
        
        try:
            while True:
                logger.info(f"Processing page {page_num} for skill: {skill}")
                
                # Extract jobs from current page
                job_cards = self.extract_job_cards()
                
                if not job_cards:
                    logger.info("No jobs found - end of results")
                    break
                
                detailed_jobs = []
                skipped_duplicates = 0
                
                for i, job_card in enumerate(job_cards):
                    try:
                        job_id = job_card['job_id']
                        
                        if job_id in self.processed_job_ids:
                            skipped_duplicates += 1
                            continue
                        
                        logger.info(f"Job {i+1}/{len(job_cards)}: {job_id}")
                        detailed_job = self.extract_detailed_job_info(job_id)
                        
                        # Mark as processed
                        self.processed_job_ids.add(job_id)
                        
                        detailed_jobs.append(detailed_job)
                        
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Failed to extract details for job {job_card['job_id']}: {e}")
                        continue
                
                logger.info(f"Page {page_num}: Extracted {len(detailed_jobs)} jobs, skipped {skipped_duplicates} duplicates")
                
                # Save results for this page immediately to single CSV file
                if detailed_jobs:
                    self.save_to_csv(detailed_jobs, skill)
                    total_jobs_extracted += len(detailed_jobs)
                    logger.info(f"Saved page {page_num}. Total: {total_jobs_extracted} jobs")
                
                # Get next page URL
                next_url = self.get_next_page_url(page_num)
                
                if not next_url:
                    break
                
                # Navigate to next page
                try:
                    self.driver.google_get(next_url, bypass_cloudflare=True)
                    time.sleep(3)
                    page_num += 1
                except Exception as e:
                    logger.error(f"Navigation failed: {e}")
                    break
        
        finally:
            # Clear current skill when done (successfully or on error)
            self.current_skill = None
        
        logger.info(f"{skill}: {total_jobs_extracted} jobs from {page_num} pages")
        return total_jobs_extracted
    


@browser(
    headless=False,
    profile="./chrome_profile",
    block_images=True,
    wait_for_complete_page_load=False
)
def scrape_indeed(driver: Driver, data):
    """Main execution function with Botasaurus"""
    indeed = IndeedSkillFilter(driver)
    
    try:
        indeed.navigate_to_jobs()
        
        available_skills = indeed.get_available_skills()
        total_jobs_all_skills = 0
        
        for idx, skill in enumerate(available_skills, 1):
            try:
                logger.info(f"\n[{idx}/{len(available_skills)}] Processing: {skill}")
                
                indeed.filter_by_skill(skill)
                jobs_count = indeed.extract_jobs_for_skill(skill)
                total_jobs_all_skills += jobs_count
                
                logger.info(f"Completed {skill}: {jobs_count} jobs")
                
                # Navigate back to main search page for next skill
                if idx < len(available_skills):
                    indeed.navigate_to_jobs()
                    time.sleep(2)
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to process '{skill}': {e}")
                continue
        
        logger.info(f"\n{'='*50}")
        logger.info(f"COMPLETE: {total_jobs_all_skills} jobs from {len(available_skills)} skills")
        logger.info(f"Output: {indeed.output_dir}")
        logger.info(f"{'='*50}")
        
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    scrape_indeed()