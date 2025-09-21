"""Main application entry point for the Automated Job Search Agent."""

import click
import logging
import sys
import os
from typing import List, Optional, Dict
from datetime import datetime

from config import load_config, Config
from job_searcher import JobSearcher
from job_processor import JobProcessor
from report_generator import ReportGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class JobSearchAgent:
    """Main job search agent orchestrator."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the job search agent."""
        self.config = load_config(config_path)
        self.searcher = JobSearcher(self.config)
        self.processor = JobProcessor(self.config)
        self.reporter = ReportGenerator(self.config)

    def run_search(self, search_terms: List[str], output_format: Optional[str] = None) -> Dict[str, str]:
        """Run the complete job search pipeline."""
        logger.info("Starting Automated Job Search Agent")
        logger.info(f"Search terms: {search_terms}")

        # Validate API configuration
        api_valid, api_message = self.config.validate_google_api()
        if not api_valid:
            logger.error(f"API Configuration Error: {api_message}")
            logger.info(self.config.get_api_setup_instructions())
            return {}

        logger.info("Google API credentials validated successfully")

        # Update configuration with current search terms
        self.config.update_search_terms(search_terms)

        # Override output format if specified
        if output_format:
            self.config.output.format = output_format

        try:
            # Step 1: Search for jobs
            logger.info("🔍 Searching for jobs across all platforms...")
            raw_jobs = self.searcher.search_jobs(search_terms)

            if not raw_jobs:
                logger.warning("❌ No jobs found matching the search criteria")
                return {}

            # Step 2: Process and filter jobs
            logger.info("⚙️ Processing and filtering job results...")
            processed_jobs = self.processor.process_jobs(raw_jobs)

            if not processed_jobs:
                logger.warning("❌ No jobs remained after filtering")
                return {}

            # Step 3: Generate reports
            logger.info("📄 Generating reports...")
            report_files = self.reporter.generate_reports(processed_jobs, search_terms)

            # Step 4: Display summary
            self._display_summary(processed_jobs, report_files)

            return report_files

        except Exception as e:
            logger.error(f"❌ Error during job search: {e}")
            raise

    def _display_summary(self, jobs: List, report_files: Dict[str, str]):
        """Display search summary to user."""
        logger.info("✅ Job search completed successfully!")
        logger.info(f"📊 Found {len(jobs)} relevant remote jobs")

        if jobs:
            companies = set(job.company for job in jobs if job.company)
            sites = set(job.source_site for job in jobs)
            avg_relevance = sum(job.relevance_score for job in jobs) / len(jobs)

            logger.info(f"🏢 Unique companies: {len(companies)}")
            logger.info(f"🌐 Job sites searched: {len(sites)}")
            logger.info(f"🎯 Average relevance score: {avg_relevance:.2f}")

        logger.info("📁 Generated reports:")
        for format_type, file_path in report_files.items():
            if file_path and os.path.exists(file_path):
                logger.info(f"   {format_type.upper()}: {file_path}")


@click.command()
@click.argument('search_terms', nargs=-1, required=True)
@click.option(
    '--config', '-c',
    default='config.yaml',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--output-format', '-f',
    type=click.Choice(['markdown', 'pdf', 'both']),
    help='Output format (overrides config setting)'
)
@click.option(
    '--max-results', '-m',
    type=int,
    help='Maximum results per site (overrides config setting)'
)
@click.option(
    '--salary-min', '-smin',
    type=int,
    help='Minimum salary filter (USD)'
)
@click.option(
    '--salary-max', '-smax',
    type=int,
    help='Maximum salary filter (USD)'
)
@click.option(
    '--exclude-keywords', '-x',
    multiple=True,
    help='Additional keywords to exclude (can be used multiple times)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '--dry-run', '-d',
    is_flag=True,
    help='Show what would be searched without actually searching'
)
def main(
    search_terms: tuple,
    config: str,
    output_format: Optional[str],
    max_results: Optional[int],
    salary_min: Optional[int],
    salary_max: Optional[int],
    exclude_keywords: tuple,
    verbose: bool,
    dry_run: bool
):
    """
    Automated Remote Job Search Agent

    Search for remote jobs across multiple platforms and generate reports.

    SEARCH_TERMS: One or more job titles or keywords to search for

    Examples:
        python main.py "software engineer" "python developer"
        python main.py "data scientist" --output-format pdf
        python main.py "product manager" --salary-min 100000 --exclude-keywords intern
    """
    # Set logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load configuration
        agent = JobSearchAgent(config)

        # Apply command line overrides
        if max_results:
            agent.config.search.max_results_per_site = max_results

        if salary_min:
            agent.config.filters.salary_minimum = salary_min

        if salary_max:
            agent.config.filters.salary_maximum = salary_max

        if exclude_keywords:
            agent.config.filters.exclude_keywords.extend([kw.lower() for kw in exclude_keywords])

        # Convert search terms to list
        search_terms_list = list(search_terms)

        if dry_run:
            # Show what would be searched
            click.echo("🔍 Dry run mode - showing search configuration:")
            click.echo(f"Search terms: {search_terms_list}")
            click.echo(f"Sites to search: {len(agent.config.all_sites)}")
            for site in agent.config.all_sites:
                click.echo(f"  - {site}")
            click.echo(f"Output format: {output_format or agent.config.output.format}")
            click.echo(f"Max results per site: {agent.config.search.max_results_per_site}")
            click.echo(f"Salary range: ${agent.config.filters.salary_minimum:,} - ${agent.config.filters.salary_maximum:,}")
            click.echo(f"Excluded keywords: {agent.config.filters.exclude_keywords}")
            return

        # Run the search
        report_files = agent.run_search(search_terms_list, output_format)

        if report_files:
            click.echo("\n🎉 Search completed successfully!")
            click.echo("📁 Generated reports:")
            for format_type, file_path in report_files.items():
                if file_path and os.path.exists(file_path):
                    click.echo(f"   {format_type.upper()}: {os.path.abspath(file_path)}")
        else:
            click.echo("❌ No jobs found or reports generated")
            sys.exit(1)

    except FileNotFoundError as e:
        click.echo(f"❌ Configuration file not found: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@click.group()
def cli():
    """Automated Remote Job Search Agent CLI"""
    pass


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
def setup(config: str):
    """Set up the job search agent with initial configuration."""
    click.echo("🛠️ Setting up Automated Job Search Agent...")

    # Check if config exists
    if os.path.exists(config):
        click.echo(f"✅ Configuration file already exists: {config}")
    else:
        click.echo(f"❌ Configuration file not found: {config}")
        click.echo("Please ensure config.yaml is in the current directory.")
        return

    # Check dependencies
    click.echo("📦 Checking dependencies...")
    try:
        import requests
        import yaml
        import bs4
        click.echo("✅ Core dependencies installed")
    except ImportError as e:
        click.echo(f"❌ Missing dependency: {e}")
        click.echo("Run: pip install -r requirements.txt")
        return

    # Test configuration loading
    try:
        from config import load_config
        config_obj = load_config(config)
        click.echo("✅ Configuration loaded successfully")
        click.echo(f"   Sites configured: {len(config_obj.all_sites)}")
        click.echo(f"   Output directory: {config_obj.output.output_dir}")
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}")
        return

    click.echo("🎉 Setup completed successfully!")
    click.echo("\n📖 Usage examples:")
    click.echo('   python main.py "software engineer"')
    click.echo('   python main.py "data scientist" "machine learning engineer" --output-format pdf')


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
def validate_api(config: str):
    """Validate Google API configuration."""
    try:
        from config import load_config
        config_obj = load_config(config)

        api_valid, api_message = config_obj.validate_google_api()

        if api_valid:
            click.echo("✅ Google API Configuration Valid")
            click.echo(f"   {api_message}")
            click.echo(f"   Daily quota: {config_obj.google_api.daily_quota} queries")
        else:
            click.echo("❌ Google API Configuration Invalid")
            click.echo(f"   {api_message}")
            click.echo(config_obj.get_api_setup_instructions())

    except Exception as e:
        click.echo(f"❌ Error validating API: {e}")


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
def list_sites(config: str):
    """List all configured job sites."""
    try:
        from config import load_config
        config_obj = load_config(config)

        click.echo("🌐 Configured Job Sites:")
        click.echo("\nATS Platforms:")
        for site in config_obj.ats_platforms:
            click.echo(f"  • {site}")

        click.echo("\nAdditional Platforms:")
        for site in config_obj.additional_platforms:
            click.echo(f"  • {site}")

        click.echo(f"\nTotal: {len(config_obj.all_sites)} sites")

    except Exception as e:
        click.echo(f"❌ Error loading configuration: {e}")


if __name__ == '__main__':
    main()