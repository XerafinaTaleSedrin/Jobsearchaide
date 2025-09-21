"""Job search engine using Google Search and web scraping."""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import concurrent.futures
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobSearcher:
    """Main job search engine that handles Google searches and web scraping."""

    def __init__(self, config: Config):
        """Initialize the job searcher with configuration."""
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def search_jobs(self, search_terms: List[str]) -> List[Dict]:
        """Search for jobs across all configured sites."""
        all_jobs = []

        logger.info(f"Starting job search for terms: {search_terms}")

        # Search each term across all sites
        for term in search_terms:
            logger.info(f"Searching for: {term}")

            # Use concurrent searches for faster execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_site = {}

                for site in self.config.all_sites:
                    future = executor.submit(self._search_site, site, term)
                    future_to_site[future] = site

                for future in concurrent.futures.as_completed(future_to_site):
                    site = future_to_site[future]
                    try:
                        jobs = future.result()
                        all_jobs.extend(jobs)
                        logger.info(f"Found {len(jobs)} jobs on {site} for '{term}'")
                    except Exception as e:
                        logger.error(f"Error searching {site} for '{term}': {e}")

            # Respect rate limiting
            time.sleep(self.config.search.request_delay)

        logger.info(f"Total jobs found before filtering: {len(all_jobs)}")
        return all_jobs

    def _search_site(self, site: str, search_term: str) -> List[Dict]:
        """Search a specific site for jobs."""
        try:
            # Build Google search query
            query = f'site:{site} "{search_term}" AND "remote"'

            # Add time filter for recent posts
            time_filter = self._get_time_filter()

            jobs = []

            if self.config.has_google_api():
                jobs = self._search_with_google_api(query, site, search_term)
            else:
                jobs = self._search_with_web_scraping(query, site, search_term)

            return jobs

        except Exception as e:
            logger.error(f"Error searching {site}: {e}")
            return []

    def _search_with_google_api(self, query: str, site: str, search_term: str) -> List[Dict]:
        """Search using Google Custom Search API."""
        try:
            from googleapiclient.discovery import build

            service = build("customsearch", "v1", developerKey=self.config.google_api.api_key)

            # Calculate date range for filtering
            since_date = datetime.now() - timedelta(hours=self.config.search.time_filter_hours)
            date_restrict = f"d{self.config.search.time_filter_hours//24 or 1}"

            result = service.cse().list(
                q=query,
                cx=self.config.google_api.search_engine_id,
                num=min(10, self.config.search.max_results_per_site),
                dateRestrict=date_restrict,
                sort="date"
            ).execute()

            jobs = []
            items = result.get('items', [])

            for item in items:
                job = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source_site': site,
                    'search_term': search_term,
                    'found_date': datetime.now().isoformat(),
                    'raw_data': item
                }
                jobs.append(job)

            return jobs

        except Exception as e:
            logger.error(f"Google API search failed for {site}: {e}")
            # Fallback to web scraping
            return self._search_with_web_scraping(query, site, search_term)

    def _search_with_web_scraping(self, query: str, site: str, search_term: str) -> List[Dict]:
        """Search using web scraping of Google search results."""
        try:
            # Encode the query for URL
            encoded_query = quote_plus(query)

            # Build Google search URL with time filter
            search_url = f"https://www.google.com/search?q={encoded_query}&tbs=qdr:d&num={min(20, self.config.search.max_results_per_site)}"

            response = self.session.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            jobs = []

            # Parse Google search results
            search_results = soup.find_all('div', class_='g')

            for result in search_results:
                try:
                    # Extract title and URL
                    title_elem = result.find('h3')
                    link_elem = result.find('a')
                    snippet_elem = result.find('span', class_='st') or result.find('div', class_='s')

                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''

                        # Filter out non-job URLs
                        if self._is_job_url(url, site):
                            job = {
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'source_site': site,
                                'search_term': search_term,
                                'found_date': datetime.now().isoformat(),
                                'raw_data': {
                                    'html_title': str(title_elem),
                                    'html_snippet': str(snippet_elem) if snippet_elem else ''
                                }
                            }
                            jobs.append(job)

                except Exception as e:
                    logger.warning(f"Error parsing search result: {e}")
                    continue

            return jobs

        except Exception as e:
            logger.error(f"Web scraping search failed for {site}: {e}")
            return []

    def _is_job_url(self, url: str, site: str) -> bool:
        """Check if URL is likely a job posting."""
        if not url or not site in url:
            return False

        # Common job posting URL patterns
        job_indicators = [
            'job', 'position', 'career', 'opening', 'opportunity',
            'vacancy', 'role', 'hiring', 'apply', 'jobs'
        ]

        url_lower = url.lower()
        return any(indicator in url_lower for indicator in job_indicators)

    def _get_time_filter(self) -> str:
        """Generate time filter string for searches."""
        hours = self.config.search.time_filter_hours
        if hours <= 24:
            return "qdr:d"  # Past day
        elif hours <= 168:  # 1 week
            return "qdr:w"
        else:
            return "qdr:m"  # Past month

    def fetch_job_details(self, job: Dict) -> Dict:
        """Fetch detailed information from a job posting URL."""
        try:
            response = self.session.get(job['url'], timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract additional details based on site
            details = self._extract_job_details(soup, job['source_site'], job['url'])

            # Merge with existing job data
            job.update(details)

            return job

        except Exception as e:
            logger.warning(f"Failed to fetch details for {job['url']}: {e}")
            return job

    def _extract_job_details(self, soup: BeautifulSoup, site: str, url: str) -> Dict:
        """Extract job details from parsed HTML based on site-specific patterns."""
        details = {
            'company': '',
            'location': '',
            'salary': '',
            'description': '',
            'requirements': '',
            'posting_date': ''
        }

        try:
            # Site-specific extraction logic
            if 'greenhouse.io' in site:
                details.update(self._extract_greenhouse_details(soup))
            elif 'lever.co' in site:
                details.update(self._extract_lever_details(soup))
            elif 'icims.com' in site:
                details.update(self._extract_icims_details(soup))
            elif 'jobvite.io' in site:
                details.update(self._extract_jobvite_details(soup))
            elif 'myworkdayjobs.com' in site:
                details.update(self._extract_workday_details(soup))
            else:
                # Generic extraction for other sites
                details.update(self._extract_generic_details(soup))

        except Exception as e:
            logger.warning(f"Error extracting details from {url}: {e}")

        return details

    def _extract_greenhouse_details(self, soup: BeautifulSoup) -> Dict:
        """Extract details from Greenhouse job postings."""
        details = {}

        # Company name
        company_elem = soup.find('span', class_='company-name')
        if company_elem:
            details['company'] = company_elem.get_text(strip=True)

        # Location
        location_elem = soup.find('div', class_='location')
        if location_elem:
            details['location'] = location_elem.get_text(strip=True)

        # Job description
        content_elem = soup.find('div', id='content')
        if content_elem:
            details['description'] = content_elem.get_text(strip=True)[:1000]

        return details

    def _extract_lever_details(self, soup: BeautifulSoup) -> Dict:
        """Extract details from Lever job postings."""
        details = {}

        # Company name
        company_elem = soup.find('div', class_='company-name') or soup.find('a', class_='company-name')
        if company_elem:
            details['company'] = company_elem.get_text(strip=True)

        # Location
        location_elem = soup.find('span', class_='location')
        if location_elem:
            details['location'] = location_elem.get_text(strip=True)

        return details

    def _extract_icims_details(self, soup: BeautifulSoup) -> Dict:
        """Extract details from iCIMS job postings."""
        details = {}

        # Job title and company often in the header
        header = soup.find('header') or soup.find('div', class_='header')
        if header:
            company_elem = header.find('h1') or header.find('h2')
            if company_elem:
                details['company'] = company_elem.get_text(strip=True)

        return details

    def _extract_jobvite_details(self, soup: BeautifulSoup) -> Dict:
        """Extract details from Jobvite job postings."""
        details = {}

        # Company name
        company_elem = soup.find('div', class_='company') or soup.find('span', class_='company')
        if company_elem:
            details['company'] = company_elem.get_text(strip=True)

        return details

    def _extract_workday_details(self, soup: BeautifulSoup) -> Dict:
        """Extract details from Workday job postings."""
        details = {}

        # Workday has specific class names
        company_elem = soup.find('span', {'data-automation-id': 'company-name'})
        if company_elem:
            details['company'] = company_elem.get_text(strip=True)

        location_elem = soup.find('span', {'data-automation-id': 'locations'})
        if location_elem:
            details['location'] = location_elem.get_text(strip=True)

        return details

    def _extract_generic_details(self, soup: BeautifulSoup) -> Dict:
        """Generic extraction for unknown sites."""
        details = {}

        # Try to find company name in common patterns
        for selector in ['h1', 'h2', '.company', '.company-name', '[class*="company"]']:
            elem = soup.select_one(selector)
            if elem and not details.get('company'):
                text = elem.get_text(strip=True)
                if len(text) < 100:  # Reasonable company name length
                    details['company'] = text
                    break

        # Extract description from main content areas
        for selector in ['main', '.content', '.description', '[class*="description"]', 'article']:
            elem = soup.select_one(selector)
            if elem and not details.get('description'):
                details['description'] = elem.get_text(strip=True)[:1000]
                break

        return details