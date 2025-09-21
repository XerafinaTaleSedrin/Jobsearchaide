"""Job data processing, filtering, and duplicate detection."""

import re
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class ProcessedJob:
    """Structured job data after processing."""
    id: str
    title: str
    company: str
    url: str
    location: str
    salary: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    description: str
    summary: str
    requirements: str
    source_site: str
    search_term: str
    posting_date: str
    found_date: str
    is_remote: bool
    relevance_score: float


class JobProcessor:
    """Handles job data processing, filtering, and duplicate detection."""

    def __init__(self, config: Config):
        """Initialize the job processor with configuration."""
        self.config = config
        self.seen_jobs: Set[str] = set()  # Track job IDs to prevent duplicates

    def process_jobs(self, raw_jobs: List[Dict]) -> List[ProcessedJob]:
        """Process raw job data into structured format with filtering and deduplication."""
        logger.info(f"Processing {len(raw_jobs)} raw jobs")

        processed_jobs = []

        for raw_job in raw_jobs:
            try:
                # Process individual job
                job = self._process_single_job(raw_job)

                if job and self._should_include_job(job):
                    # Check for duplicates
                    if job.id not in self.seen_jobs:
                        processed_jobs.append(job)
                        self.seen_jobs.add(job.id)
                    else:
                        logger.debug(f"Duplicate job filtered: {job.title} at {job.company}")

            except Exception as e:
                logger.warning(f"Error processing job: {e}")
                continue

        logger.info(f"Processed jobs: {len(processed_jobs)} (after filtering and deduplication)")
        return processed_jobs

    def _process_single_job(self, raw_job: Dict) -> Optional[ProcessedJob]:
        """Process a single raw job into structured format."""
        try:
            # Extract basic information
            title = self._clean_text(raw_job.get('title', ''))
            company = self._clean_text(raw_job.get('company', ''))
            url = raw_job.get('url', '')
            location = self._clean_text(raw_job.get('location', ''))
            description = self._clean_text(raw_job.get('description', '') or raw_job.get('snippet', ''))

            # Generate unique ID for duplicate detection
            job_id = self._generate_job_id(title, company, url)

            # Extract and parse salary information
            salary_text = self._clean_text(raw_job.get('salary', ''))
            salary_min, salary_max = self._parse_salary(salary_text + ' ' + description)

            # Generate job summary
            summary = self._generate_summary(description)

            # Extract requirements
            requirements = self._extract_requirements(description)

            # Calculate relevance score
            relevance_score = self._calculate_relevance(raw_job, title, description)

            # Check if job is truly remote
            is_remote = self._verify_remote_status(title, description, location)

            return ProcessedJob(
                id=job_id,
                title=title,
                company=company,
                url=url,
                location=location,
                salary=salary_text,
                salary_min=salary_min,
                salary_max=salary_max,
                description=description,
                summary=summary,
                requirements=requirements,
                source_site=raw_job.get('source_site', ''),
                search_term=raw_job.get('search_term', ''),
                posting_date=raw_job.get('posting_date', ''),
                found_date=raw_job.get('found_date', datetime.now().isoformat()),
                is_remote=is_remote,
                relevance_score=relevance_score
            )

        except Exception as e:
            logger.error(f"Error processing single job: {e}")
            return None

    def _generate_job_id(self, title: str, company: str, url: str) -> str:
        """Generate a unique ID for duplicate detection."""
        # Use URL if available, otherwise combine title and company
        if url:
            # Extract the meaningful part of URL for ID generation
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')

            # Look for job ID in URL path or query parameters
            job_id_from_url = None

            # Check query parameters for job IDs
            query_params = parse_qs(parsed_url.query)
            for param in ['id', 'job_id', 'jobId', 'posting_id']:
                if param in query_params:
                    job_id_from_url = query_params[param][0]
                    break

            # If no ID in query, look in path
            if not job_id_from_url:
                for part in reversed(path_parts):
                    if part and (part.isdigit() or len(part) > 10):
                        job_id_from_url = part
                        break

            if job_id_from_url:
                return hashlib.md5(f"{parsed_url.netloc}_{job_id_from_url}".encode()).hexdigest()[:16]

        # Fallback to title + company hash
        combined = f"{title.lower()}_{company.lower()}".replace(' ', '_')
        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # Remove HTML entities and tags if any
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'<[^>]+>', ' ', text)

        return text

    def _parse_salary(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract salary range from text."""
        if not text:
            return None, None

        # Common salary patterns
        salary_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[-–—to]+\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $100,000 - $150,000
            r'\$(\d{1,3}(?:,\d{3})*)\s*[-–—]\s*(\d{1,3}(?:,\d{3})*)',  # $100,000-150,000
            r'(\d{1,3}(?:,\d{3})*)\s*[-–—to]+\s*(\d{1,3}(?:,\d{3})*)\s*(?:USD|dollars?|per\s+year|annually)',  # 100,000 - 150,000 USD
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:per\s+year|annually|/year|yr)',  # $100,000 per year
            r'(\d{1,3}(?:,\d{3})*)\s*k\s*[-–—to]+\s*(\d{1,3}(?:,\d{3})*)\s*k',  # 100k - 150k
        ]

        for pattern in salary_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match.groups()) == 2:
                        # Range found
                        min_sal = int(match.group(1).replace(',', '').replace('.', ''))
                        max_sal = int(match.group(2).replace(',', '').replace('.', ''))

                        # Handle 'k' notation
                        if 'k' in match.group(0).lower():
                            min_sal *= 1000
                            max_sal *= 1000

                        # Validate reasonable salary range
                        if 10000 <= min_sal <= 1000000 and 10000 <= max_sal <= 1000000:
                            return min_sal, max_sal
                    else:
                        # Single salary found
                        salary = int(match.group(1).replace(',', '').replace('.', ''))
                        if 'k' in match.group(0).lower():
                            salary *= 1000

                        if 10000 <= salary <= 1000000:
                            return salary, salary
                except (ValueError, IndexError):
                    continue

        return None, None

    def _generate_summary(self, description: str) -> str:
        """Generate a concise summary from job description."""
        if not description:
            return ""

        # Split into sentences
        sentences = re.split(r'[.!?]+', description)

        # Take first few sentences that contain key information
        summary_sentences = []
        important_keywords = [
            'responsible', 'role', 'position', 'seeking', 'looking', 'opportunity',
            'experience', 'skills', 'requirements', 'qualifications', 'team'
        ]

        for sentence in sentences[:5]:  # Check first 5 sentences
            sentence = sentence.strip()
            if sentence and len(sentence) > 20:
                # Prioritize sentences with important keywords
                if any(keyword in sentence.lower() for keyword in important_keywords):
                    summary_sentences.append(sentence)
                elif len(summary_sentences) == 0:
                    # Take first meaningful sentence if no keyword match yet
                    summary_sentences.append(sentence)

                # Limit summary length
                if len(' '.join(summary_sentences)) > self.config.output.max_summary_length:
                    break

        summary = ' '.join(summary_sentences)

        # Truncate if still too long
        if len(summary) > self.config.output.max_summary_length:
            summary = summary[:self.config.output.max_summary_length].rsplit(' ', 1)[0] + '...'

        return summary

    def _extract_requirements(self, description: str) -> str:
        """Extract key requirements from job description."""
        if not description:
            return ""

        # Look for requirements sections
        req_patterns = [
            r'(?:requirements?|qualifications?|skills?)[:\-\s]*([^.]*(?:\.[^.]*){0,3})',
            r'(?:you\s+(?:will\s+)?(?:need|have|bring))[:\-\s]*([^.]*(?:\.[^.]*){0,2})',
            r'(?:must\s+have|required)[:\-\s]*([^.]*(?:\.[^.]*){0,2})'
        ]

        requirements = []

        for pattern in req_patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE | re.DOTALL)
            for match in matches:
                req_text = match.group(1).strip()
                if req_text and len(req_text) > 10:
                    requirements.append(req_text)

        return '; '.join(requirements[:3])  # Top 3 requirement matches

    def _calculate_relevance(self, raw_job: Dict, title: str, description: str) -> float:
        """Calculate job relevance score based on search term matching."""
        search_term = raw_job.get('search_term', '').lower()
        if not search_term:
            return 0.5

        score = 0.0
        text_to_search = f"{title} {description}".lower()

        # Exact match in title gets highest score
        if search_term in title.lower():
            score += 0.5

        # Partial match in title
        search_words = search_term.split()
        title_words = title.lower().split()
        title_matches = sum(1 for word in search_words if word in title_words)
        score += (title_matches / len(search_words)) * 0.3

        # Matches in description
        desc_matches = sum(1 for word in search_words if word in text_to_search)
        score += (desc_matches / len(search_words)) * 0.2

        return min(score, 1.0)

    def _verify_remote_status(self, title: str, description: str, location: str) -> bool:
        """Verify if job is actually remote."""
        text_to_check = f"{title} {description} {location}".lower()

        # Positive remote indicators
        remote_indicators = [
            'remote', 'telecommute', 'work from home', 'wfh', 'distributed',
            'virtual', 'anywhere', 'location independent'
        ]

        # Negative indicators (not truly remote)
        non_remote_indicators = [
            'hybrid', 'on-site', 'in-person', 'office', 'local', 'commute',
            'relocation', 'visa sponsorship'
        ]

        has_remote = any(indicator in text_to_check for indicator in remote_indicators)
        has_non_remote = any(indicator in text_to_check for indicator in non_remote_indicators)

        return has_remote and not has_non_remote

    def _should_include_job(self, job: ProcessedJob) -> bool:
        """Determine if job should be included based on filters."""
        # Check keyword exclusions
        text_to_check = f"{job.title} {job.description}".lower()
        for excluded_keyword in self.config.filters.exclude_keywords:
            if excluded_keyword in text_to_check:
                logger.debug(f"Job filtered by keyword '{excluded_keyword}': {job.title}")
                return False

        # Check experience level exclusions
        for excluded_level in self.config.filters.exclude_experience_levels:
            if excluded_level in text_to_check:
                logger.debug(f"Job filtered by experience level '{excluded_level}': {job.title}")
                return False

        # Check salary range if available
        if job.salary_min and job.salary_max:
            if (job.salary_max < self.config.filters.salary_minimum or
                job.salary_min > self.config.filters.salary_maximum):
                logger.debug(f"Job filtered by salary range: {job.title} (${job.salary_min}-${job.salary_max})")
                return False

        # Must be verified as remote
        if not job.is_remote:
            logger.debug(f"Job filtered as not truly remote: {job.title}")
            return False

        return True

    def get_duplicate_stats(self) -> Dict[str, int]:
        """Get statistics about duplicate detection."""
        return {
            'unique_jobs_seen': len(self.seen_jobs),
            'total_processed': len(self.seen_jobs)
        }