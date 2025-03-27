#!/usr/bin/env python3
"""
Test runner script for the Psychic Source Transcript Analysis Tool.
Discovers and runs all unit tests in the project.
"""
import unittest
import sys
import os

def run_tests():
    """Discover and run all tests in the project."""
    # Add the project root to the path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Discover all tests in the tests directory
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests()) 