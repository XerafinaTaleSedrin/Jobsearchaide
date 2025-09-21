"""Quick test script without Unicode emojis for Windows compatibility."""

import sys
import os

def test_system():
    """Quick system test."""
    print("=== JOB SEARCH AGENT QUICK TEST ===")

    tests_passed = 0
    total_tests = 0

    # Test 1: Configuration
    total_tests += 1
    print("\n1. Testing configuration...")
    try:
        from config import load_config
        config = load_config()
        print("   PASS - Configuration loaded")
        print(f"   Sites: {len(config.all_sites)}")
        tests_passed += 1
    except Exception as e:
        print(f"   FAIL - {e}")

    # Test 2: API validation
    total_tests += 1
    print("\n2. Testing API configuration...")
    try:
        api_valid, msg = config.validate_google_api()
        if api_valid:
            print("   PASS - API configured")
        else:
            print("   WARN - API not configured")
            print(f"   {msg}")
        tests_passed += 1
    except Exception as e:
        print(f"   FAIL - {e}")

    # Test 3: Components
    total_tests += 1
    print("\n3. Testing components...")
    try:
        from job_searcher import JobSearcher
        from job_processor import JobProcessor
        from report_generator import ReportGenerator
        from alternative_sources import AlternativeJobSources

        searcher = JobSearcher(config)
        processor = JobProcessor(config)
        reporter = ReportGenerator(config)
        alt_sources = AlternativeJobSources(config)

        print("   PASS - All components loaded")
        tests_passed += 1
    except Exception as e:
        print(f"   FAIL - {e}")

    # Test 4: Mock processing
    total_tests += 1
    print("\n4. Testing job processing...")
    try:
        mock_job = {
            'title': 'Test Engineer',
            'url': 'https://test.com/job/123',
            'snippet': 'Remote software engineer position',
            'source_site': 'test.com',
            'search_term': 'engineer',
            'found_date': '2024-01-01T00:00:00'
        }

        processed = processor.process_jobs([mock_job])
        if processed:
            print("   PASS - Job processing works")
            tests_passed += 1
        else:
            print("   FAIL - No jobs processed")
    except Exception as e:
        print(f"   FAIL - {e}")

    # Test 5: Report generation
    total_tests += 1
    print("\n5. Testing report generation...")
    try:
        if 'processed' in locals() and processed:
            reports = reporter.generate_reports(processed, ['test'])
            if reports:
                print("   PASS - Reports generated")
                for fmt, path in reports.items():
                    if os.path.exists(path):
                        print(f"   Created: {fmt} -> {path}")
                tests_passed += 1
            else:
                print("   FAIL - No reports generated")
        else:
            print("   SKIP - No processed jobs")
    except Exception as e:
        print(f"   FAIL - {e}")

    # Summary
    print(f"\n=== RESULTS: {tests_passed}/{total_tests} tests passed ===")

    if tests_passed == total_tests:
        print("SUCCESS - System is ready!")
    elif tests_passed >= 3:
        print("PARTIAL - System should work with limitations")
    else:
        print("FAILURE - System has major issues")

    # Recommendations
    print("\nRECOMMENDATIONS:")
    if not config.has_google_api():
        print("- Set up Google API for reliable results: python main.py validate-api")
    else:
        print("- Try a real search: python main.py \"software engineer\"")

    return tests_passed >= 3

if __name__ == "__main__":
    success = test_system()
    sys.exit(0 if success else 1)