"""Alternative job search sources for backup and enhanced coverage."""

import requests
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import time

logger = logging.getLogger(__name__)


class AlternativeJobSources:
    """Provides alternative job search methods beyond Google API."""

    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'JobSearchAgent/1.0 (Professional Job Search Tool)'
        })

    def search_all_alternatives(self, search_terms: List[str]) -> List[Dict]:
        """Search all alternative sources and return combined results."""
        all_jobs = []

        for term in search_terms:
            logger.info(f"Searching alternative sources for: {term}")

            # RSS Feeds
            rss_jobs = self._search_rss_feeds(term)
            all_jobs.extend(rss_jobs)

            # Indeed API (if available)
            indeed_jobs = self._search_indeed_api(term)
            all_jobs.extend(indeed_jobs)

            # AngelList/Wellfound API
            angellist_jobs = self._search_angellist_api(term)
            all_jobs.extend(angellist_jobs)

            # Remote-specific job boards
            remote_jobs = self._search_remote_boards(term)
            all_jobs.extend(remote_jobs)

            # Add delay between searches
            time.sleep(self.config.search.request_delay)

        logger.info(f"Alternative sources found {len(all_jobs)} total jobs")
        return all_jobs

    def _search_rss_feeds(self, search_term: str) -> List[Dict]:
        """Search job RSS feeds."""
        jobs = []

        # Known job RSS feeds
        rss_feeds = [
            {
                'url': 'https://www.indeed.com/rss?q={}&l=Remote',
                'site': 'indeed.com'
            },
            {
                'url': 'https://remoteok.io/remote-jobs.rss',
                'site': 'remoteok.io'
            },
            {
                'url': 'https://weworkremotely.com/remote-jobs.rss',
                'site': 'weworkremotely.com'
            },
            {
                'url': 'https://jobs.github.com/positions.rss?search={}+remote',
                'site': 'github.com/jobs'
            }
        ]

        for feed_info in rss_feeds:
            try:
                feed_url = feed_info['url'].format(quote_plus(search_term))
                logger.debug(f"Fetching RSS feed: {feed_url}")

                response = self.session.get(feed_url, timeout=10)
                response.raise_for_status()

                # Parse RSS XML
                root = ET.fromstring(response.content)

                # Handle different RSS formats
                items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

                for item in items[:10]:  # Limit to 10 per feed
                    job = self._parse_rss_item(item, feed_info['site'], search_term)
                    if job and self._is_recent_job(job.get('posting_date', '')):
                        jobs.append(job)

                logger.info(f"RSS feed {feed_info['site']}: {len(jobs)} jobs")

            except Exception as e:
                logger.warning(f"RSS feed error for {feed_info['site']}: {e}")

        return jobs

    def _parse_rss_item(self, item: ET.Element, site: str, search_term: str) -> Optional[Dict]:
        """Parse an RSS item into job format."""
        try:
            # Extract basic info (handles both RSS and Atom formats)
            title_elem = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
            link_elem = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
            desc_elem = item.find('description') or item.find('{http://www.w3.org/2005/Atom}summary')
            date_elem = item.find('pubDate') or item.find('{http://www.w3.org/2005/Atom}published')

            if not title_elem or not link_elem:
                return None

            title = title_elem.text or ''
            link = link_elem.text if hasattr(link_elem, 'text') else link_elem.get('href', '')
            description = (desc_elem.text or '') if desc_elem is not None else ''
            pub_date = (date_elem.text or '') if date_elem is not None else ''

            # Filter for remote and search term relevance
            text_to_check = f"{title} {description}".lower()
            if 'remote' not in text_to_check:
                return None

            if search_term.lower() not in text_to_check:
                return None

            return {
                'title': title,
                'url': link,
                'snippet': description[:200],
                'source_site': site,
                'search_term': search_term,
                'posting_date': pub_date,
                'found_date': datetime.now().isoformat(),
                'raw_data': {'rss_item': ET.tostring(item, encoding='unicode')}
            }

        except Exception as e:
            logger.warning(f"Error parsing RSS item: {e}")
            return None

    def _search_indeed_api(self, search_term: str) -> List[Dict]:
        """Search Indeed API (placeholder for future implementation)."""
        # Indeed deprecated their API, but could use their RSS or partner APIs
        logger.debug("Indeed API search - not implemented (API deprecated)")
        return []

    def _search_angellist_api(self, search_term: str) -> List[Dict]:
        """Search AngelList/Wellfound API (placeholder)."""
        # Would require AngelList API key
        logger.debug("AngelList API search - not implemented (requires API key)")
        return []

    def _search_remote_boards(self, search_term: str) -> List[Dict]:
        """Search dedicated remote job boards."""
        jobs = []

        # Remote-specific job boards with simple scraping
        remote_boards = [
            {
                'name': 'RemoteOK',
                'search_url': 'https://remoteok.io/api',
                'parser': self._parse_remoteok_api
            },
            {
                'name': 'We Work Remotely',
                'search_url': 'https://weworkremotely.com/remote-jobs/search?term={}',
                'parser': self._parse_wwr_html
            }
        ]

        for board in remote_boards:
            try:
                board_jobs = board['parser'](search_term, board)
                jobs.extend(board_jobs)
                time.sleep(1)  # Be respectful with requests
            except Exception as e:
                logger.warning(f"Error searching {board['name']}: {e}")

        return jobs

    def _parse_remoteok_api(self, search_term: str, board_info: Dict) -> List[Dict]:
        """Parse RemoteOK API response."""
        try:
            response = self.session.get(board_info['search_url'], timeout=10)
            response.raise_for_status()

            jobs_data = response.json()
            jobs = []

            for job_data in jobs_data[:20]:  # Limit results
                if not isinstance(job_data, dict):
                    continue

                title = job_data.get('position', '')
                company = job_data.get('company', '')
                description = job_data.get('description', '')

                # Filter by search term
                text_to_check = f"{title} {company} {description}".lower()
                if search_term.lower() not in text_to_check:
                    continue

                # Check if recent (within filter timeframe)
                date_str = job_data.get('date', '')
                if not self._is_recent_job(date_str):
                    continue

                job = {
                    'title': title,
                    'url': f"https://remoteok.io/remote-jobs/{job_data.get('id', '')}",
                    'snippet': description[:200],
                    'source_site': 'remoteok.io',
                    'search_term': search_term,
                    'company': company,
                    'location': 'Remote',
                    'salary': job_data.get('salary_min', ''),
                    'posting_date': date_str,
                    'found_date': datetime.now().isoformat(),
                    'raw_data': job_data
                }
                jobs.append(job)

            logger.info(f"RemoteOK: {len(jobs)} jobs found")
            return jobs

        except Exception as e:
            logger.warning(f"RemoteOK API error: {e}")
            return []

    def _parse_wwr_html(self, search_term: str, board_info: Dict) -> List[Dict]:
        """Parse We Work Remotely HTML (simplified scraping)."""
        try:
            from bs4 import BeautifulSoup

            search_url = board_info['search_url'].format(quote_plus(search_term))
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            jobs = []

            # Look for job listings (basic pattern)
            job_elements = soup.find_all('li', class_='feature') or soup.find_all('div', class_='job')

            for job_elem in job_elements[:10]:
                try:
                    title_elem = job_elem.find('h2') or job_elem.find('a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '') if title_elem.name == 'a' else ''

                    if link and not link.startswith('http'):
                        link = 'https://weworkremotely.com' + link

                    company_elem = job_elem.find('h3') or job_elem.find('.company')
                    company = company_elem.get_text(strip=True) if company_elem else ''

                    job = {
                        'title': title,
                        'url': link,
                        'snippet': '',
                        'source_site': 'weworkremotely.com',
                        'search_term': search_term,
                        'company': company,
                        'location': 'Remote',
                        'posting_date': '',
                        'found_date': datetime.now().isoformat(),
                        'raw_data': {'html': str(job_elem)}
                    }
                    jobs.append(job)

                except Exception as e:
                    logger.debug(f"Error parsing WWR job element: {e}")

            logger.info(f"We Work Remotely: {len(jobs)} jobs found")
            return jobs

        except Exception as e:
            logger.warning(f"We Work Remotely scraping error: {e}")
            return []

    def _is_recent_job(self, date_str: str) -> bool:
        """Check if job posting is within the configured time filter."""
        if not date_str:
            return True  # Assume recent if no date

        try:
            # Try different date formats
            date_formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%a, %d %b %Y %H:%M:%S %z'
            ]

            job_date = None
            for fmt in date_formats:
                try:
                    job_date = datetime.strptime(date_str.strip(), fmt)
                    break
                except ValueError:
                    continue

            if not job_date:
                return True  # Can't parse date, assume recent

            # Check if within time filter
            cutoff_date = datetime.now() - timedelta(hours=self.config.search.time_filter_hours)
            return job_date >= cutoff_date

        except Exception as e:
            logger.debug(f"Date parsing error for '{date_str}': {e}")
            return True  # Assume recent on error

    def test_alternative_sources(self) -> Dict[str, bool]:
        """Test connectivity to alternative sources."""
        results = {}

        # Test RSS feeds
        test_feeds = [
            ('RemoteOK RSS', 'https://remoteok.io/remote-jobs.rss'),
            ('We Work Remotely RSS', 'https://weworkremotely.com/remote-jobs.rss'),
        ]

        for name, url in test_feeds:
            try:
                response = self.session.get(url, timeout=5)
                results[name] = response.status_code == 200
            except Exception:
                results[name] = False

        # Test API endpoints
        api_tests = [
            ('RemoteOK API', 'https://remoteok.io/api'),
        ]

        for name, url in api_tests:
            try:
                response = self.session.get(url, timeout=5)
                results[name] = response.status_code == 200
            except Exception:
                results[name] = False

        return results