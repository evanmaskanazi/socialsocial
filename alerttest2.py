#!/usr/bin/env python3
"""
Alert Diagnostic Script - Standard Library Only
No external dependencies needed (no requests, no httpx)
"""

import urllib.request
import urllib.parse
import json
import http.cookiejar

BASE_URL = "https://socialsocial-72gn.onrender.com"

def make_request(url, method='GET', data=None, cookies=None):
    """Make HTTP request using only stdlib"""
    
    # Setup cookie handling
    if cookies is None:
        cookies = http.cookiejar.CookieJar()
    
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies)
    )
    
    # Prepare request
    full_url = BASE_URL + url
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Python-Diagnostic/1.0'
    }
    
    if data:
        data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(
        full_url,
        data=data,
        headers=headers,
        method=method
    )
    
    try:
        response = opener.open(req)
        response_data = response.read().decode('utf-8')
        return json.loads(response_data), response.status, cookies
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        error_body = e.read().decode('utf-8')
        print(f"Response: {error_body}")
        return None, e.code, cookies
    except Exception as e:
        print(f"Error: {e}")
        return None, 0, cookies

def main():
    print("=" * 70)
    print("THERASOCIAL ALERT DIAGNOSTIC - API TESTING")
    print("=" * 70)
    
    # Step 1: Login as Alice
    print("\n1️⃣ LOGGING IN AS ALICE")
    print("-" * 70)
    
    username = input("Enter Alice's username (default: alice): ").strip() or "alice"
    password = input("Enter Alice's password: ").strip()
    
    login_data = {
        "username": username,
        "password": password
    }
    
    result, status, cookies = make_request('/api/auth/login', 'POST', login_data)
    
    if status == 200:
        print(f"✅ Login successful!")
        print(f"User ID: {result.get('user_id')}")
        print(f"Username: {result.get('username')}")
    else:
        print(f"❌ Login failed with status {status}")
        return
    
    # Step 2: Get alerts
    print("\n2️⃣ FETCHING ALERTS")
    print("-" * 70)
    
    alerts_data, status, _ = make_request('/api/alerts', 'GET', cookies=cookies)
    
    if status == 200 and alerts_data:
        alert_list = alerts_data.get('alerts', [])
        unread_count = alerts_data.get('unread_count', 0)
        
        print(f"Total alerts: {len(alert_list)}")
        print(f"Unread count: {unread_count}")
        
        if alert_list:
            print("\nAlert Details:")
            for i, alert in enumerate(alert_list, 1):
                print(f"\n  Alert #{i}:")
                print(f"    ID: {alert.get('id')}")
                print(f"    Title: {alert.get('title')}")
                print(f"    Message: {alert.get('message', 'N/A')[:100]}")
                print(f"    Type: {alert.get('type')}")
                print(f"    Read: {alert.get('is_read')}")
                print(f"    Created: {alert.get('created_at')}")
        else:
            print("❌ No alerts found")
    else:
        print(f"❌ Failed to fetch alerts (status: {status})")
    
    # Step 3: Get user profile
    print("\n3️⃣ FETCHING USER PROFILE")
    print("-" * 70)
    
    profile_data, status, _ = make_request('/api/user/profile', 'GET', cookies=cookies)
    
    if status == 200 and profile_data:
        print(f"User ID: {profile_data.get('id')}")
        print(f"Username: {profile_data.get('username')}")
        print(f"Email: {profile_data.get('email')}")
        print(f"Language: {profile_data.get('preferred_language', 'en')}")
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
