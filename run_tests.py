#!/usr/bin/env python3
"""
run_tests.py - Test runner for the project

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py -v                 # Verbose output
    python run_tests.py -k "test_parse"    # Run specific tests
    python run_tests.py --cov              # With coverage report
    python run_tests.py --quick            # Quick smoke test (subset)
"""

import argparse
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Run project tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword")
    parser.add_argument("--cov", action="store_true", help="Generate coverage report")
    parser.add_argument("--quick", action="store_true", help="Quick smoke test")
    parser.add_argument("--file", help="Run specific test file")
    args = parser.parse_args()

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    if args.verbose:
        cmd.append("-v")

    if args.keyword:
        cmd.extend(["-k", args.keyword])

    if args.cov:
        cmd.extend(["--cov=utils", "--cov-report=html", "--cov-report=term"])

    if args.quick:
        # Run only a subset of quick tests
        cmd.extend(["-k", "test_parse or test_safe or test_basic"])

    if args.file:
        cmd.append(args.file)
    else:
        cmd.append("tests/")

    # Add common options
    cmd.extend(["--tb=short", "-x"])  # Short traceback, stop on first failure

    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)) or ".")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
