#!/usr/bin/env python3
"""
Memory System Test Runner

Runs all memory system tests with proper categorization and reporting.
"""

import sys
import os
import subprocess
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def run_test_suite(name, markers, verbose=True):
    """Run a test suite with specific markers"""
    print_header(f"{name} Tests")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v" if verbose else "",
        "--tb=short",
        "--color=yes",
        "-m", markers,
        "--disable-warnings"
    ]
    
    # Remove empty strings
    cmd = [c for c in cmd if c]
    
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
    
    return result.returncode == 0


def run_all_tests():
    """Run all test suites"""
    print_header("Memory System Test Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # 1. Unit Tests (fast, isolated)
    print("\n📦 Running Unit Tests...")
    results['unit'] = run_test_suite("Unit", "unit")
    
    # 2. Integration Tests (requires database)
    print("\n🔗 Running Integration Tests...")
    results['integration'] = run_test_suite("Integration", "integration and requires_db")
    
    # 3. End-to-End Tests (complete workflows)
    print("\n🎯 Running End-to-End Tests...")
    results['e2e'] = run_test_suite("End-to-End", "e2e and requires_db")
    
    # 4. Legacy Tests (original test_memory_services.py)
    print("\n📋 Running Legacy Tests...")
    cmd = ["python", "tests/test_memory_services.py"]
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
    results['legacy'] = result.returncode == 0
    
    # Summary
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print("Test Suite Results:")
    for suite, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {suite.ljust(15)}: {status}")
    
    print(f"\nTotal: {total} suites")
    print(f"Passed: {passed} suites")
    print(f"Failed: {failed} suites")
    
    if failed == 0:
        print("\n🎉 All test suites passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test suite(s) failed")
        return 1


def run_quick_tests():
    """Run only fast unit tests"""
    print_header("Quick Test Suite (Unit Tests Only)")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes",
        "-m", "unit",
        "--disable-warnings"
    ]
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
    return result.returncode


def run_coverage_tests():
    """Run tests with coverage report"""
    print_header("Test Coverage Analysis")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes",
        "--cov=services/memory",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--disable-warnings"
    ]
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
    
    if result.returncode == 0:
        print("\n📊 Coverage report generated in htmlcov/index.html")
    
    return result.returncode


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run memory system tests")
    parser.add_argument(
        "--mode",
        choices=["all", "quick", "unit", "integration", "e2e", "coverage"],
        default="all",
        help="Test mode to run"
    )
    
    args = parser.parse_args()
    
    if args.mode == "quick":
        return run_quick_tests()
    elif args.mode == "unit":
        return 0 if run_test_suite("Unit", "unit") else 1
    elif args.mode == "integration":
        return 0 if run_test_suite("Integration", "integration and requires_db") else 1
    elif args.mode == "e2e":
        return 0 if run_test_suite("End-to-End", "e2e and requires_db") else 1
    elif args.mode == "coverage":
        return run_coverage_tests()
    else:  # all
        return run_all_tests()


if __name__ == "__main__":
    sys.exit(main())