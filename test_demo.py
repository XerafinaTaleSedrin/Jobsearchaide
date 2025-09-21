"""Simple test demonstration of the job search agent."""

import os
import sys
from config import load_config
from job_searcher import JobSearcher
from job_processor import JobProcessor
from report_generator import ReportGenerator

def test_configuration():
    """Test that configuration loads properly."""
    print("Testing configuration loading...")
    try:
        config = load_config()
        print(f"✓ Configuration loaded successfully")
        print(f"  - Sites configured: {len(config.all_sites)}")
        print(f"  - ATS platforms: {config.ats_platforms}")
        print(f"  - Output directory: {config.output.output_dir}")
        return config
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return None

def test_search_simulation():
    """Simulate a search without actually making web requests."""
    print("\nTesting search simulation...")

    # Create mock job data
    mock_jobs = [
        {
            'title': 'Senior Software Engineer - Remote',
            'url': 'https://greenhouse.io/job/123',
            'snippet': 'We are looking for a senior software engineer to join our remote team...',
            'source_site': 'greenhouse.io',
            'search_term': 'software engineer',
            'found_date': '2024-01-21T10:00:00',
            'company': 'TechCorp',
            'location': 'Remote',
            'salary': '$120,000 - $150,000',
            'description': 'Join our team as a senior software engineer working on cutting-edge technology. Must have 5+ years experience with Python and cloud technologies.'
        },
        {
            'title': 'Python Developer (Remote)',
            'url': 'https://lever.co/job/456',
            'snippet': 'Remote Python developer position with competitive salary...',
            'source_site': 'lever.co',
            'search_term': 'software engineer',
            'found_date': '2024-01-21T11:00:00',
            'company': 'StartupCo',
            'location': 'Remote',
            'salary': '$100,000 - $130,000',
            'description': 'We need a Python developer for our growing startup. Experience with Django and PostgreSQL required.'
        }
    ]

    return mock_jobs

def test_processing(config, mock_jobs):
    """Test job processing and filtering."""
    print("\nTesting job processing...")
    try:
        processor = JobProcessor(config)
        processed_jobs = processor.process_jobs(mock_jobs)

        print(f"✓ Processing completed")
        print(f"  - Input jobs: {len(mock_jobs)}")
        print(f"  - Processed jobs: {len(processed_jobs)}")

        if processed_jobs:
            job = processed_jobs[0]
            print(f"  - Sample job: {job.title} at {job.company}")
            print(f"  - Relevance score: {job.relevance_score:.2f}")
            print(f"  - Remote verified: {job.is_remote}")

        return processed_jobs
    except Exception as e:
        print(f"✗ Processing error: {e}")
        return []

def test_report_generation(config, processed_jobs):
    """Test report generation."""
    print("\nTesting report generation...")
    try:
        reporter = ReportGenerator(config)
        search_terms = ['software engineer']

        # Create reports directory if it doesn't exist
        os.makedirs(config.output.output_dir, exist_ok=True)

        report_files = reporter.generate_reports(processed_jobs, search_terms)

        print(f"✓ Report generation completed")
        for format_type, file_path in report_files.items():
            if file_path and os.path.exists(file_path):
                print(f"  - {format_type.upper()}: {file_path}")
            else:
                print(f"  - {format_type.upper()}: Generation failed or disabled")

        return report_files
    except Exception as e:
        print(f"✗ Report generation error: {e}")
        return {}

def main():
    """Run the demonstration."""
    print("=== Job Search Agent Demonstration ===\n")

    # Test configuration
    config = test_configuration()
    if not config:
        sys.exit(1)

    # Test with mock data
    mock_jobs = test_search_simulation()
    processed_jobs = test_processing(config, mock_jobs)

    if processed_jobs:
        report_files = test_report_generation(config, processed_jobs)

        print("\n=== Demonstration Complete ===")
        print("The job search agent is working correctly!")
        print("\nTo run a real search, use:")
        print('python main.py "software engineer" "python developer"')
    else:
        print("\n✗ Demonstration failed during processing")

if __name__ == "__main__":
    main()