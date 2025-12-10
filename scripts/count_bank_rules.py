#!/usr/bin/env python3
"""Quick script to count bank rules in the database"""

import os
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "super-secret-long-random-string")

def count_rules_for_pharmacy(pharmacy_id: int):
    """Count rules for a specific pharmacy"""
    url = f"{API_BASE_URL}/bank-rules/pharmacies/{pharmacy_id}/bank-rules"
    headers = {'X-API-Key': API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            rules = response.json()
            active = sum(1 for r in rules if r.get('is_active', True))
            inactive = len(rules) - active
            return {
                'total': len(rules),
                'active': active,
                'inactive': inactive,
                'rules': rules
            }
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("🔍 Counting bank rules...\n")
    
    # Check pharmacy 1 (most common)
    result = count_rules_for_pharmacy(1)
    
    if result:
        print(f"📊 Bank Rules for Pharmacy 1:")
        print(f"  Total rules: {result['total']}")
        print(f"  Active rules: {result['active']}")
        print(f"  Inactive rules: {result['inactive']}")
        
        if result['total'] > 0:
            print(f"\n📋 Rule Names:")
            for rule in result['rules']:
                status = "✅" if rule.get('is_active', True) else "❌"
                print(f"  {status} [{rule.get('priority', 'N/A')}] {rule.get('name', 'Unknown')}")
    else:
        print("❌ Could not fetch rules. Check API connection and credentials.")
