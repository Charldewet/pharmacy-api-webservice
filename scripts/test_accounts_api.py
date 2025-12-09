#!/usr/bin/env python3
"""
Test the accounts API endpoint to verify accounts are loaded.
"""

import sys
import os
import requests
from pathlib import Path

# Get API key from command line or use provided one
API_KEY = sys.argv[1] if len(sys.argv) > 1 else "super-secret-long-random-string"

# Try to determine API URL
# Check if there's an environment variable or default to localhost
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

print("=" * 70)
print("TESTING ACCOUNTS API ENDPOINT")
print("=" * 70)
print()
print(f"API Base URL: {API_BASE_URL}")
print(f"API Key: {API_KEY[:20]}...")
print()

headers = {
    "X-API-Key": API_KEY,
    "Authorization": f"Bearer {API_KEY}"
}

# Test 1: List all accounts
print("Test 1: GET /accounts")
print("-" * 70)
try:
    response = requests.get(
        f"{API_BASE_URL}/accounts",
        headers=headers,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        accounts = response.json()
        print(f"✓ Success! Found {len(accounts)} accounts")
        print()
        if accounts:
            print("Sample accounts (first 5):")
            for acc in accounts[:5]:
                print(f"  - {acc.get('code')}: {acc.get('name')} ({acc.get('type')})")
        else:
            print("⚠️  Warning: No accounts returned")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Could not connect to API")
    print("   Make sure the API server is running")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print()

# Test 2: Get accounts summary stats
print("Test 2: GET /accounts/summary/stats")
print("-" * 70)
try:
    response = requests.get(
        f"{API_BASE_URL}/accounts/summary/stats",
        headers=headers,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        stats = response.json()
        print("✓ Success! Summary statistics:")
        print(f"  Total accounts: {stats.get('total', 0)}")
        print(f"  Active accounts: {stats.get('active', 0)}")
        print(f"  Inactive accounts: {stats.get('inactive', 0)}")
        print()
        print("Accounts by type:")
        for acc_type, count in stats.get('by_type', {}).items():
            print(f"  {acc_type}: {count}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Could not connect to API")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print()

# Test 3: Filter by type
print("Test 3: GET /accounts?type=INCOME")
print("-" * 70)
try:
    response = requests.get(
        f"{API_BASE_URL}/accounts",
        headers=headers,
        params={"type": "INCOME"},
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        accounts = response.json()
        print(f"✓ Success! Found {len(accounts)} INCOME accounts")
        if accounts:
            print("Income accounts:")
            for acc in accounts:
                print(f"  - {acc.get('code')}: {acc.get('name')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Could not connect to API")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 70)
print("TESTING COMPLETE")
print("=" * 70)

