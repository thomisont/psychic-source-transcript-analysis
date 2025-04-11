import requests
import json
import os
import time
from urllib.parse import urljoin

def get_server_url():
    """Try to get the server URL from various sources"""
    # Try environment variable
    env_url = os.environ.get('REPLIT_URL')
    if env_url:
        return env_url
        
    # Try common Replit URLs for this workspace
    replit_urls = [
        'https://psychic-source-elevenlabs.replit.app',
        'https://2cf5c75a-53c7-4770-ac2c-693998adbe64-00-eks0n7ucya4l.kirk.replit.dev',
        'http://localhost:8080',
        'http://0.0.0.0:8080'
    ]
    
    # Try to find an active server
    for url in replit_urls:
        try:
            response = requests.get(urljoin(url, '/api-status'), timeout=2)
            if response.status_code == 200:
                data = response.json()
                # Return the URL reported by the server itself
                if 'base_url' in data:
                    print(f"Found active server at: {data['base_url']}")
                    return data['base_url']
                return url
        except:
            continue
            
    # Default to the first Replit URL if we couldn't find an active server
    return replit_urls[0]

def test_api(retries=3, delay=1):
    """Test API endpoints and trigger refreshes with retries"""
    server_url = get_server_url()
    print(f"\nTesting API endpoints on {server_url}")
    
    # First check API status
    status_url = urljoin(server_url, '/api-status')
    print(f"\nChecking API status: {status_url}")
    try:
        response = requests.get(status_url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"API Status: {json.dumps(data, indent=2)}")
            
            # Use the base_url from the response if available
            if 'base_url' in data:
                server_url = data['base_url']
                print(f"Using server URL from response: {server_url}")
    except Exception as e:
        print(f"Error checking API status: {e}")
    
    # Test main endpoints
    endpoints = [
        '/api/themes-sentiment/data?timeframe=last_30_days',
        '/api/dashboard/stats?timeframe=last_30_days'
    ]
    
    for endpoint in endpoints:
        url = urljoin(server_url, endpoint)
        print(f"\nTesting: {url}")
        
        attempt = 0
        while attempt < retries:
            try:
                response = requests.get(url, timeout=10)
                print(f"Status: {response.status_code}")
                data = response.json()
                
                if response.status_code == 200:
                    # Print the first part of the response for inspection
                    print(f"Response preview: {json.dumps(data, indent=2)[:200]}...")
                    
                    # Check if the response indicates an error or is missing data
                    if 'error' in data:
                        print(f"API returned error: {data['error']}")
                    elif endpoint.startswith('/api/themes-sentiment') and all(len(data.get('data', {}).get(key, [])) == 0 for key in ['sentiment_over_time', 'top_themes']):
                        print("API returned empty themes data")
                    elif endpoint.startswith('/api/dashboard/stats') and data.get('total_conversations', 0) == 0:
                        print("API returned empty dashboard data")
                    else:
                        print("API returned valid data")
                        break
                    
                # If there's an issue, let's immediately try the refresh endpoint
                if endpoint.startswith('/api/themes-sentiment'):
                    print("Trying to refresh themes data...")
                    break
                
            except Exception as e:
                print(f"Error (attempt {attempt+1}/{retries}): {e}")
                
            attempt += 1
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    # Trigger refresh for themes/sentiment
    refresh_url = urljoin(server_url, '/api/themes-sentiment/refresh')
    print(f"\nTriggering refresh: {refresh_url}")
    try:
        response = requests.post(refresh_url, json={"timeframe": "last_30_days"}, timeout=20)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Refresh response: {json.dumps(data, indent=2)}")
            
            # After refresh, check if we now have data
            themes_url = urljoin(server_url, '/api/themes-sentiment/data?timeframe=last_30_days')
            print(f"\nVerifying data after refresh: {themes_url}")
            time.sleep(2)  # Give the server a moment to process
            try:
                response = requests.get(themes_url, timeout=10)
                data = response.json()
                
                if response.status_code == 200:
                    if all(len(data.get('data', {}).get(key, [])) == 0 for key in ['sentiment_over_time', 'top_themes']):
                        print("Still no themes data after refresh")
                    else:
                        print("Successfully retrieved themes data after refresh!")
                        print(f"Data sample: {json.dumps(data, indent=2)[:200]}...")
            except Exception as e:
                print(f"Error verifying after refresh: {e}")
    except Exception as e:
        print(f"Error triggering refresh: {e}")

if __name__ == "__main__":
    test_api() 