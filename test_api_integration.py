#!/usr/bin/env python3
"""
Script to test the ElevenLabs API integration.
Run this script to verify that the API client is working correctly.
"""
import sys
import os
import logging
from app.utils.test_api import APITester

def main():
    """Run the API tests and display results."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n==== ELEVENLABS API INTEGRATION TEST ====")
    print("Testing connection and API endpoints...\n")
    
    # Run tests
    tester = APITester()
    results = tester.run_all_tests()
    
    # Print results in a readable format
    print("\n==== TEST RESULTS ====")
    print(f"Overall: {'✓ SUCCESS' if results['success'] else '✗ FAILED'}")
    print("\nDetailed Results:")
    for test, result in results['results'].items():
        print(f"  {test}: {'✓ PASSED' if result else '✗ FAILED'}")
    
    # Show troubleshooting tips if any tests failed
    if not results['success']:
        print("\nTroubleshooting Tips:")
        print("  1. Check that your API key is valid in the .env file")
        print("  2. Verify that the agent ID is correct")
        print("  3. Ensure you have network connectivity to the ElevenLabs API")
        print("  4. Check the logs for detailed error messages")
    
    print("\nTest completed.")
    return 0 if results['success'] else 1

if __name__ == "__main__":
    sys.exit(main()) 