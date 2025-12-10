#!/usr/bin/env python3
"""
Script to add new bank rules using account codes.
"""

import os
import requests
from typing import Dict, List, Optional

API_BASE_URL = os.getenv("API_BASE_URL", "https://pharmacy-api-webservice.onrender.com")
API_KEY = os.getenv("API_KEY", "super-secret-long-random-string")

def get_all_accounts() -> Dict[str, Dict]:
    """Get all accounts via API as code -> {id, type, name} mapping"""
    url = f"{API_BASE_URL}/accounts?is_active=true"
    headers = {'X-API-Key': API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            accounts = response.json()
            result = {}
            # Map by code
            for acc in accounts:
                code = acc.get('code')
                if code:
                    result[code] = {'id': acc['id'], 'type': acc['type'], 'name': acc['name']}
            # Also map by name for backwards compatibility
            for acc in accounts:
                result[acc['name']] = {'id': acc['id'], 'type': acc['type'], 'code': acc.get('code')}
            return result
        else:
            print(f"❌ Failed to fetch accounts: {response.status_code}: {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Error fetching accounts: {str(e)}")
        return {}

def create_rule_via_api(rule_data: Dict) -> bool:
    """Create a rule via the API"""
    url = f"{API_BASE_URL}/bank-rules/pharmacies/{rule_data['pharmacy_id']}/bank-rules"
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    }
    
    try:
        response = requests.post(url, json=rule_data, headers=headers)
        if response.status_code in [200, 201]:
            print(f"✅ Created: {rule_data['name']} (priority {rule_data.get('priority', 'N/A')})")
            return True
        else:
            print(f"❌ Failed: {rule_data['name']} - {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating {rule_data['name']}: {str(e)}")
        return False

def main():
    """Main function"""
    rules_json = {
        "rules": [
            {
                "name": "Card settlements (EFTPOS CR) → Takings Clearing",
                "type": "receive",
                "priority": 1,
                "conditions": [
                    {
                        "group_type": "ALL",
                        "field": "description",
                        "operator": "contains",
                        "value": "EFTPOS SETTLEMENT CR"
                    }
                ],
                "allocate": [
                    { "account_code": "1400", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Card Settlement"
            },
            {
                "name": "Card settlement reversals (EFTPOS DR) → Takings Clearing",
                "type": "receive",
                "priority": 2,
                "conditions": [
                    {
                        "group_type": "ALL",
                        "field": "description",
                        "operator": "contains",
                        "value": "EFTPOS SETTLEMENT DR"
                    }
                ],
                "allocate": [
                    { "account_code": "1400", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Card Settlement Reversal"
            },
            {
                "name": "Cash deposits (Autosafe / ATM) → Takings Clearing",
                "type": "receive",
                "priority": 3,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "CASH DEP"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "AUTOSAFE"
                    }
                ],
                "allocate": [
                    { "account_code": "1400", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Cash Deposit"
            },
            {
                "name": "Medical Aid Script Claims → Script Debtors",
                "type": "receive",
                "priority": 4,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "MEDICAL"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "SCRIPT CLAIM"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "DISCOVERY"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "MEDSCHEME"
                    }
                ],
                "allocate": [
                    { "account_code": "1100", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Medical Aid"
            },
            {
                "name": "Interest Received → Interest Income",
                "type": "receive",
                "priority": 5,
                "conditions": [
                    {
                        "group_type": "ALL",
                        "field": "description",
                        "operator": "contains",
                        "value": "INTEREST"
                    }
                ],
                "allocate": [
                    { "account_code": "4220", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Bank"
            },
            {
                "name": "Bank Charges → Bank Fees",
                "type": "spend",
                "priority": 10,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "BANK CHARGES"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "SERVICE FEE"
                    }
                ],
                "allocate": [
                    { "account_code": "6050", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Bank"
            },
            {
                "name": "POS Fees → POS Charges",
                "type": "spend",
                "priority": 11,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "POS FEE"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "MERCHANT FEE"
                    }
                ],
                "allocate": [
                    { "account_code": "5200", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Bank"
            },
            {
                "name": "Loan Repayments → Loan Accounts (Split Capital & Interest)",
                "type": "spend",
                "priority": 12,
                "conditions": [
                    {
                        "group_type": "ALL",
                        "field": "description",
                        "operator": "contains",
                        "value": "LOAN"
                    }
                ],
                "allocate": [
                    { "account_code": "2200", "percent": 80, "vat_code": "NO_VAT" },
                    { "account_code": "4220", "percent": 20, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Bank Loan"
            },
            {
                "name": "Supplier Payments (Wholesalers) → Cost of Sales",
                "type": "spend",
                "priority": 13,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "UPD"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "MEDPRO"
                    }
                ],
                "allocate": [
                    { "account_code": "5000", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Wholesaler"
            },
            {
                "name": "Salaries & Wages → Salary Expense",
                "type": "spend",
                "priority": 14,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "SALARY"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "PAYROLL"
                    }
                ],
                "allocate": [
                    { "account_code": "6000", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Staff"
            },
            {
                "name": "Municipality Payments → Water & Electricity",
                "type": "spend",
                "priority": 15,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "MUNICIPAL"
                    },
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "COUNCIL"
                    }
                ],
                "allocate": [
                    { "account_code": "6200", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Municipality"
            },
            {
                "name": "Insurance Payments → Insurance Expense",
                "type": "spend",
                "priority": 16,
                "conditions": [
                    {
                        "group_type": "ALL",
                        "field": "description",
                        "operator": "contains",
                        "value": "INSURANCE"
                    }
                ],
                "allocate": [
                    { "account_code": "6470", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Insurance"
            },
            {
                "name": "Owner Drawings → Owners Equity",
                "type": "spend",
                "priority": 17,
                "conditions": [
                    {
                        "group_type": "ALL",
                        "field": "description",
                        "operator": "contains",
                        "value": "OWNER"
                    }
                ],
                "allocate": [
                    { "account_code": "3000", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Owner"
            },
            {
                "name": "Transfer Between Accounts",
                "type": "transfer",
                "priority": 30,
                "conditions": [
                    {
                        "group_type": "ANY",
                        "field": "description",
                        "operator": "contains",
                        "value": "TRANSFER"
                    }
                ],
                "allocate": [
                    { "account_code": "1000", "percent": 100, "vat_code": "NO_VAT" }
                ],
                "contact_name": "Internal Transfer"
            }
        ]
    }
    
    pharmacy_id = 1
    
    print("🔍 Loading accounts via API...")
    accounts_map = get_all_accounts()
    print(f"✅ Found {len(accounts_map)} accounts")
    
    print(f"\n📝 Processing {len(rules_json['rules'])} rules...\n")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for rule_json in rules_json['rules']:
        # Convert rule format
        api_conditions = []
        for cond in rule_json['conditions']:
            api_conditions.append({
                'group_type': cond.get('group_type', 'ALL'),
                'field': cond['field'],
                'operator': cond['operator'],
                'value': cond['value']
            })
        
        # Convert allocations
        api_allocate = []
        for alloc in rule_json['allocate']:
            account_code = alloc.get('account_code')
            if not account_code:
                print(f"⚠️  Warning: No account_code in allocation. Skipping rule '{rule_json['name']}'")
                skipped_count += 1
                break
            
            account_info = accounts_map.get(account_code)
            if not account_info:
                print(f"⚠️  Warning: Account code '{account_code}' not found. Skipping rule '{rule_json['name']}'")
                skipped_count += 1
                break
            
            api_allocate.append({
                'account_id': account_info['id'],
                'percent': alloc['percent'],
                'vat_code': alloc.get('vat_code', 'NO_VAT')
            })
        else:
            # Only create if we didn't break
            api_rule = {
                'pharmacy_id': pharmacy_id,
                'name': rule_json['name'],
                'type': rule_json['type'],
                'priority': rule_json.get('priority', 100),
                'contact_name': rule_json.get('contact_name'),
                'conditions': api_conditions,
                'allocate': api_allocate
            }
            
            if create_rule_via_api(api_rule):
                success_count += 1
            else:
                failed_count += 1
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Created: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  ⚠️  Skipped: {skipped_count}")

if __name__ == "__main__":
    main()
