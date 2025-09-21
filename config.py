"""Configuration management for the job search agent."""

import yaml
import os
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class SearchSettings:
    """Search configuration settings."""
    time_filter_hours: int
    max_results_per_site: int
    request_delay: float


@dataclass
class FilterSettings:
    """Job filtering settings."""
    exclude_keywords: List[str]
    salary_minimum: int
    salary_maximum: int
    exclude_experience_levels: List[str]


@dataclass
class OutputSettings:
    """Output configuration settings."""
    format: str
    output_dir: str
    filename_template: str
    include_summaries: bool
    max_summary_length: int


@dataclass
class GoogleAPISettings:
    """Google API configuration."""
    api_key: str
    search_engine_id: str
    daily_quota: int


class Config:
    """Main configuration class for the job search agent."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file."""
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # Parse search settings
        search_data = config_data.get('search_settings', {})
        self.search = SearchSettings(
            time_filter_hours=search_data.get('time_filter_hours', 24),
            max_results_per_site=search_data.get('max_results_per_site', 50),
            request_delay=search_data.get('request_delay', 2.0)
        )

        # Parse job sites
        sites_data = config_data.get('job_sites', {})
        self.ats_platforms = sites_data.get('ats_platforms', [])
        self.additional_platforms = sites_data.get('additional_platforms', [])
        self.all_sites = self.ats_platforms + self.additional_platforms

        # Default search terms
        self.default_searches = config_data.get('default_searches', [])

        # Parse filter settings
        filter_data = config_data.get('filters', {})
        salary_ranges = filter_data.get('salary_ranges', {})
        self.filters = FilterSettings(
            exclude_keywords=[kw.lower() for kw in filter_data.get('exclude_keywords', [])],
            salary_minimum=salary_ranges.get('minimum', 0),
            salary_maximum=salary_ranges.get('maximum', 1000000),
            exclude_experience_levels=[level.lower() for level in filter_data.get('exclude_experience_levels', [])]
        )

        # Parse output settings
        output_data = config_data.get('output', {})
        self.output = OutputSettings(
            format=output_data.get('format', 'both'),
            output_dir=output_data.get('output_dir', './reports'),
            filename_template=output_data.get('filename_template', 'job_search_{timestamp}_{search_term}'),
            include_summaries=output_data.get('include_summaries', True),
            max_summary_length=output_data.get('max_summary_length', 300)
        )

        # Parse Google API settings
        google_data = config_data.get('google_api', {})
        self.google_api = GoogleAPISettings(
            api_key=google_data.get('api_key', ''),
            search_engine_id=google_data.get('search_engine_id', ''),
            daily_quota=google_data.get('daily_quota', 100)
        )

        # Create output directory if it doesn't exist
        os.makedirs(self.output.output_dir, exist_ok=True)

    def has_google_api(self) -> bool:
        """Check if Google API credentials are configured."""
        return bool(self.google_api.api_key and self.google_api.search_engine_id)

    def validate_google_api(self) -> tuple[bool, str]:
        """Validate Google API credentials and return status with message."""
        if not self.google_api.api_key:
            return False, "Google API key is missing. Please add it to config.yaml"

        if not self.google_api.search_engine_id:
            return False, "Google Search Engine ID is missing. Please add it to config.yaml"

        # Basic format validation
        if len(self.google_api.api_key) < 20:
            return False, "Google API key appears to be invalid (too short)"

        if len(self.google_api.search_engine_id) < 10:
            return False, "Google Search Engine ID appears to be invalid (too short)"

        return True, "Google API credentials appear to be configured correctly"

    def get_api_setup_instructions(self) -> str:
        """Get detailed API setup instructions."""
        return """
🔧 Google Custom Search API Setup Instructions:

1. GET API KEY:
   • Go to: https://console.cloud.google.com/
   • Create or select a project
   • Enable "Custom Search API"
   • Go to "Credentials" → "Create Credentials" → "API Key"
   • Copy the API key

2. GET SEARCH ENGINE ID:
   • Go to: https://cse.google.com/cse/
   • Click "Add" to create a new search engine
   • For "Sites to search": enter "*" (search entire web) or specific job sites
   • Click "Create"
   • Copy the "Search engine ID"

3. UPDATE CONFIG:
   • Edit config.yaml
   • Paste API key in google_api.api_key
   • Paste Search Engine ID in google_api.search_engine_id

4. QUOTA LIMITS:
   • Free tier: 100 queries/day
   • Paid tier: $5 per 1000 queries
   • Each job site search uses 1 query

⚠️  Without API credentials, the job search will return zero results!
"""

    def update_search_terms(self, search_terms: List[str]):
        """Update the search terms for this session."""
        self.current_search_terms = search_terms

    def get_search_terms(self) -> List[str]:
        """Get current search terms or default if none set."""
        return getattr(self, 'current_search_terms', self.default_searches)


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from file."""
    return Config(config_path)