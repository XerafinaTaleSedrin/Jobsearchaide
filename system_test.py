"""Comprehensive system test for the job search agent."""

import os
import sys
import logging
from typing import Dict, List

# Set up logging for testing
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run_comprehensive_test():
    """Run a comprehensive test of the entire job search system."""
    print("=" * 60)
    print("COMPREHENSIVE JOB SEARCH AGENT TEST")
    print("=" * 60)

    test_results = {}

    # Test 1: Configuration Loading
    print("\n1. Testing Configuration Loading...")
    try:
        from config import load_config
        config = load_config()
        print("PASS Configuration loaded successfully")
        print(f"   - {len(config.all_sites)} job sites configured")
        print(f"   - Output directory: {config.output.output_dir}")
        test_results['config_loading'] = True
    except Exception as e:
        print(f"FAIL Configuration loading failed: {e}")
        test_results['config_loading'] = False
        return test_results

    # Test 2: Google API Validation
    print("\n2. Testing Google API Configuration...")
    api_valid, api_message = config.validate_google_api()
    if api_valid:
        print("PASS Google API configuration is valid")
        print(f"   - {api_message}")
        test_results['api_config'] = True
    else:
        print("WARN Google API configuration issues:")
        print(f"   - {api_message}")
        print("   - This will limit job search results")
        test_results['api_config'] = False

    # Test 3: Alternative Sources Connectivity
    print("\n3. Testing Alternative Job Sources...")
    try:
        from alternative_sources import AlternativeJobSources
        alt_sources = AlternativeJobSources(config)
        source_results = alt_sources.test_alternative_sources()

        available_sources = sum(source_results.values())
        total_sources = len(source_results)

        for source, status in source_results.items():
            status_icon = "PASS" if status else "FAIL"
            print(f"   {status_icon} {source}")

        print(f"   Summary: {available_sources}/{total_sources} alternative sources available")
        test_results['alternative_sources'] = available_sources > 0

    except Exception as e:
        print(f"❌ Alternative sources test failed: {e}")
        test_results['alternative_sources'] = False

    # Test 4: Job Processing Components
    print("\n4️⃣ Testing Job Processing Components...")
    try:
        from job_processor import JobProcessor
        from job_searcher import JobSearcher
        from report_generator import ReportGenerator

        # Test component initialization
        processor = JobProcessor(config)
        searcher = JobSearcher(config)
        reporter = ReportGenerator(config)

        print("✅ All processing components initialized successfully")
        test_results['components'] = True

    except Exception as e:
        print(f"❌ Component initialization failed: {e}")
        test_results['components'] = False

    # Test 5: Mock Job Processing
    print("\n5️⃣ Testing Job Processing with Mock Data...")
    try:
        # Create mock job data
        mock_jobs = [
            {
                'title': 'Senior Software Engineer - Remote',
                'url': 'https://greenhouse.io/job/test-123',
                'snippet': 'We are looking for a senior software engineer to join our remote team. Must have 5+ years experience with Python.',
                'source_site': 'greenhouse.io',
                'search_term': 'software engineer',
                'found_date': '2024-01-21T10:00:00',
                'company': 'TechCorp',
                'location': 'Remote',
                'salary': '$120,000 - $150,000',
                'description': 'Join our team as a senior software engineer working on cutting-edge technology.'
            },
            {
                'title': 'Data Scientist (Remote)',
                'url': 'https://lever.co/job/test-456',
                'snippet': 'Remote data scientist position with machine learning focus...',
                'source_site': 'lever.co',
                'search_term': 'data scientist',
                'found_date': '2024-01-21T11:00:00',
                'company': 'DataCorp',
                'location': 'Remote',
                'salary': '$130,000 - $160,000',
                'description': 'Work with large datasets and build predictive models.'
            }
        ]

        # Process mock jobs
        processed_jobs = processor.process_jobs(mock_jobs)

        if processed_jobs:
            print(f"✅ Mock job processing successful")
            print(f"   - Processed {len(processed_jobs)} jobs")
            print(f"   - Sample job: {processed_jobs[0].title}")
            print(f"   - Relevance score: {processed_jobs[0].relevance_score:.2f}")
            test_results['job_processing'] = True
        else:
            print("❌ Mock job processing returned no results")
            test_results['job_processing'] = False

    except Exception as e:
        print(f"❌ Job processing test failed: {e}")
        test_results['job_processing'] = False

    # Test 6: Report Generation
    print("\n6️⃣ Testing Report Generation...")
    try:
        if test_results.get('job_processing') and processed_jobs:
            search_terms = ['software engineer', 'data scientist']
            report_files = reporter.generate_reports(processed_jobs, search_terms)

            generated_reports = []
            for format_type, file_path in report_files.items():
                if file_path and os.path.exists(file_path):
                    generated_reports.append(format_type)
                    print(f"   ✅ {format_type.upper()} report: {file_path}")

            if generated_reports:
                print(f"✅ Report generation successful ({', '.join(generated_reports)})")
                test_results['report_generation'] = True
            else:
                print("❌ No reports were generated successfully")
                test_results['report_generation'] = False
        else:
            print("⚠️  Skipped report generation (no processed jobs)")
            test_results['report_generation'] = False

    except Exception as e:
        print(f"❌ Report generation test failed: {e}")
        test_results['report_generation'] = False

    # Test 7: CLI Commands
    print("\n7️⃣ Testing CLI Commands...")
    try:
        # Test that main CLI imports work
        from main import JobSearchAgent

        # Initialize agent
        agent = JobSearchAgent()
        print("✅ CLI components loaded successfully")
        test_results['cli'] = True

    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        test_results['cli'] = False

    # Test Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed_tests = sum(test_results.values())
    total_tests = len(test_results)

    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")

    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! System is ready for use.")
        return_code = 0
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  MOST TESTS PASSED. System should work with minor limitations.")
        return_code = 0
    else:
        print("❌ MULTIPLE TEST FAILURES. System may not work properly.")
        return_code = 1

    # Provide recommendations
    print("\n💡 RECOMMENDATIONS:")

    if not test_results.get('api_config'):
        print("   🔧 Set up Google API credentials for reliable job search results")
        print("      Run: python main.py validate-api")

    if not test_results.get('alternative_sources'):
        print("   🔧 Check internet connectivity for alternative job sources")

    if test_results.get('api_config') and test_results.get('components'):
        print("   🚀 System is ready! Try: python main.py \"software engineer\"")

    print(f"\n📝 Detailed logs saved in system test output above")

    return test_results


def quick_connectivity_test():
    """Quick test of basic connectivity and configuration."""
    print("🔍 Quick Connectivity Test...")

    try:
        import requests
        response = requests.get("https://www.google.com", timeout=5)
        print("✅ Internet connectivity: OK")
    except:
        print("❌ Internet connectivity: FAILED")

    try:
        from config import load_config
        config = load_config()
        print("✅ Configuration loading: OK")
    except Exception as e:
        print(f"❌ Configuration loading: FAILED ({e})")

    try:
        from alternative_sources import AlternativeJobSources
        print("✅ Alternative sources module: OK")
    except Exception as e:
        print(f"❌ Alternative sources module: FAILED ({e})")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_connectivity_test()
    else:
        test_results = run_comprehensive_test()

        # Exit with appropriate code
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)

        if passed_tests < total_tests * 0.8:
            sys.exit(1)
        else:
            sys.exit(0)