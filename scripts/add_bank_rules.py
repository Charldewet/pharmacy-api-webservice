#!/usr/bin/env python3
"""
Script to add bank rules from JSON format to the database.
Converts account names to account IDs and creates rules via API.
"""

import json
import sys
import os
import requests
from typing import Dict, List, Optional

# API base URL - adjust if needed
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "super-secret-long-random-string")

# Account name to VAT code mapping based on account type
# Common VAT codes: NO_VAT, STANDARD (15%), ZERO_RATED (0%), EXEMPT
VAT_CODE_MAPPING = {
    # Income accounts - typically ZERO_RATED or STANDARD
    "Takings Clearing": "ZERO_RATED",
    "Interest Received": "NO_VAT",
    "Inter-Account Transfers": "NO_VAT",
    
    # Expense accounts - typically STANDARD or ZERO_RATED
    "Purchases – Dispensary": "STANDARD",
    "Purchases – Front Shop": "STANDARD",
    "Wages & Salaries": "NO_VAT",
    "Staff Costs": "NO_VAT",
    "Staff Advances": "NO_VAT",
    "Utilities – Electricity/Water": "STANDARD",
    "Telephone & Internet": "STANDARD",
    "Rent – Premises": "STANDARD",
    "Insurance Expense": "STANDARD",
    "Security": "STANDARD",
    "Motor Vehicle – Fuel": "STANDARD",
    "Courier & Postage": "STANDARD",
    "Software & IT Services": "STANDARD",
    "Bank Charges": "NO_VAT",
    "Interest Paid": "NO_VAT",
    "Petty Cash": "NO_VAT",
    "Cost of Sales – Vouchers/Airtime": "STANDARD",
    
    # Tax accounts
    "VAT Payable (Settlement)": "NO_VAT",
    "Payroll Taxes Payable": "NO_VAT",
    
    # Owner/Equity accounts
    "Owner's Drawings": "NO_VAT",
    "Intercompany Clearing": "NO_VAT",
    
    # Suspense/Review accounts
    "Suspense – Review Needed": "NO_VAT",
    "Transfers In": "NO_VAT",
    "Transfers Out": "NO_VAT",
}

def get_vat_code_for_account(account_name: str, account_type: Optional[str] = None) -> str:
    """Determine VAT code based on account name and type"""
    # Check explicit mapping first
    if account_name in VAT_CODE_MAPPING:
        return VAT_CODE_MAPPING[account_name]
    
    # Default based on account type if available
    if account_type:
        if account_type in ['INCOME', 'COGS']:
            return "ZERO_RATED"  # Most income is zero-rated
        elif account_type == 'EXPENSE':
            return "STANDARD"  # Most expenses have VAT
        elif account_type in ['ASSET', 'LIABILITY', 'EQUITY']:
            return "NO_VAT"
    
    # Default fallback
    return "NO_VAT"

def get_all_accounts() -> Dict[str, Dict]:
    """Get all accounts via API as name -> {id, type, code} and code -> {id, type, name} mapping"""
    url = f"{API_BASE_URL}/accounts?is_active=true"
    headers = {'X-API-Key': API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            accounts = response.json()
            result = {}
            # Map by name
            for acc in accounts:
                result[acc['name']] = {'id': acc['id'], 'type': acc['type'], 'code': acc.get('code')}
            # Also map by code
            for acc in accounts:
                code = acc.get('code')
                if code:
                    result[code] = {'id': acc['id'], 'type': acc['type'], 'name': acc['name']}
            return result
        else:
            print(f"❌ Failed to fetch accounts: {response.status_code}: {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Error fetching accounts: {str(e)}")
        return {}

def convert_rule_format(rule_json: Dict, accounts_map: Dict[str, int], pharmacy_id: int = 1) -> Optional[Dict]:
    """Convert JSON rule format to API format"""
    # Support both old format (conditions_all/conditions_any) and new format (conditions array)
    if 'conditions' in rule_json and rule_json['conditions']:
        # New format: conditions array with group_type in each condition
        api_conditions = []
        for cond in rule_json['conditions']:
            api_conditions.append({
                'group_type': cond.get('group_type', 'ALL'),
                'field': cond['field'],
                'operator': cond['operator'],
                'value': cond['value']
            })
    elif 'conditions_all' in rule_json and rule_json['conditions_all']:
        # Old format: conditions_all
        group_type = 'ALL'
        conditions = rule_json['conditions_all']
        api_conditions = []
        for cond in conditions:
            api_conditions.append({
                'group_type': group_type,
                'field': cond['field'],
                'operator': cond['operator'],
                'value': cond['value']
            })
    elif 'conditions_any' in rule_json and rule_json['conditions_any']:
        # Old format: conditions_any
        group_type = 'ANY'
        conditions = rule_json['conditions_any']
        api_conditions = []
        for cond in conditions:
            api_conditions.append({
                'group_type': group_type,
                'field': cond['field'],
                'operator': cond['operator'],
                'value': cond['value']
            })
    else:
        # Empty conditions - use ALL with empty list
        api_conditions = []
    
    # Convert allocations
    api_allocate = []
    for alloc in rule_json['allocate']:
        # Support both 'account' (name) and 'account_code' (code)
        account_name = alloc.get('account')
        account_code = alloc.get('account_code')
        
        account_info = None
        lookup_key = None
        
        if account_code:
            # Look up by account code
            account_info = accounts_map.get(account_code)
            lookup_key = account_code
        elif account_name:
            # Look up by account name
            account_info = accounts_map.get(account_name)
            lookup_key = account_name
        
        if not account_info:
            print(f"⚠️  Warning: Account '{lookup_key}' (name: {account_name}, code: {account_code}) not found. Skipping rule '{rule_json['name']}'")
            return None
        
        account_id = account_info['id'] if isinstance(account_info, dict) else account_info
        account_type = account_info.get('type') if isinstance(account_info, dict) else None
        actual_account_name = account_info.get('name', lookup_key) if isinstance(account_info, dict) else lookup_key
        
        vat_code = alloc.get('vat_code') or get_vat_code_for_account(actual_account_name, account_type)
        
        api_allocate.append({
            'account_id': account_id,
            'percent': alloc['percent'],
            'vat_code': vat_code
        })
    
    # Build API request
    api_rule = {
        'pharmacy_id': pharmacy_id,
        'name': rule_json['name'],
        'type': rule_json['type'],
        'priority': rule_json.get('priority', 100),
        'contact_name': rule_json.get('contact'),
        'conditions': api_conditions,
        'allocate': api_allocate
    }
    
    return api_rule

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
            print(f"✅ Created: {rule_data['name']}")
            return True
        else:
            print(f"❌ Failed: {rule_data['name']} - {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating {rule_data['name']}: {str(e)}")
        return False

def main():
    """Main function"""
    # Rules JSON from user - using account codes
    rules_json = {
        "rules": [
            {
                "name": "Card settlements (EFTPOS CR) → Takings Clearing",
                "type": "receive",
                "conditions_all": [
                    {"field": "description", "operator": "contains", "value": "EFTPOS SETTLEMENT CR"}
                ],
                "allocate": [{"account": "Takings Clearing", "percent": 100}],
                "contact": "Card Settlement"
            },
            {
                "name": "Card settlement reversals (EFTPOS DR) → Takings Clearing",
                "type": "spend",
                "conditions_all": [
                    {"field": "description", "operator": "contains", "value": "EFTPOS SETTLEMENT DR"}
                ],
                "allocate": [{"account": "Takings Clearing", "percent": 100}],
                "contact": "Card Settlement Reversal"
            },
            {
                "name": "SnapScan/Yoco/PayFast settlement → Takings Clearing",
                "type": "receive",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "SNAPSCAN"},
                    {"field": "description", "operator": "contains", "value": "YOCO"},
                    {"field": "description", "operator": "contains", "value": "PAYFAST"},
                    {"field": "description", "operator": "contains", "value": "ZAPPER"}
                ],
                "allocate": [{"account": "Takings Clearing", "percent": 100}],
                "contact": "Alt Card Settlement"
            },
            {
                "name": "Bank transfer IN → Transfers In",
                "type": "receive",
                "conditions_any": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TRANSFER\\s+FROM\\b"},
                    {"field": "description", "operator": "regex", "value": "\\bTRANSFER\\s+FROM\\b"}
                ],
                "allocate": [{"account": "Inter-Account Transfers", "percent": 100}],
                "contact": "Internal Transfer In"
            },
            {
                "name": "Bank transfer OUT → Transfers Out",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TRANSFER\\s+TO\\b"},
                    {"field": "description", "operator": "regex", "value": "\\bTRANSFER\\s+TO\\b"}
                ],
                "allocate": [{"account": "Inter-Account Transfers", "percent": 100}],
                "contact": "Internal Transfer Out"
            },
            {
                "name": "IB TO CJ → Owner Drawings",
                "type": "spend",
                "conditions_all": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TO\\s+CJ\\b"}
                ],
                "allocate": [{"account": "Owner's Drawings", "percent": 100}],
                "contact": "CJ"
            },
            {
                "name": "IB TO MARIA → Staff advance",
                "type": "spend",
                "conditions_all": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TO\\s+MARIA\\b"}
                ],
                "allocate": [{"account": "Staff Advances", "percent": 100}],
                "contact": "Maria"
            },
            {
                "name": "IB TO IDEXIS → Software/IT services",
                "type": "spend",
                "conditions_all": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TO\\s+IDEXIS\\b"}
                ],
                "allocate": [{"account": "Software & IT Services", "percent": 100}],
                "contact": "Idexis"
            },
            {
                "name": "IB TO TRANSPHARM → Pharma supplier",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TO\\s+TRANSPHARM\\b"},
                    {"field": "description", "operator": "contains", "value": "TRANSPHARM"}
                ],
                "allocate": [{"account": "Purchases – Dispensary", "percent": 100}],
                "contact": "Transpharm"
            },
            {
                "name": "IB TO BASSOPA → Intercompany",
                "type": "spend",
                "conditions_all": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TO\\s+BASSOPA\\b"}
                ],
                "allocate": [{"account": "Intercompany Clearing", "percent": 100}],
                "contact": "Bassopa (Interco)"
            },
            {
                "name": "Generic 'IB TO <NAME>' → Manual review",
                "type": "spend",
                "conditions_all": [
                    {"field": "description", "operator": "regex", "value": "\\bIB\\s+TO\\s+[A-Z]+"}
                ],
                "allocate": [{"account": "Suspense – Review Needed", "percent": 100}],
                "contact": "Unmapped IB TO"
            },
            {
                "name": "UPD / Alpha / Transpharm → Purchases (Dispensary)",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "UPD"},
                    {"field": "description", "operator": "contains", "value": "ALPHA PHARM"},
                    {"field": "description", "operator": "contains", "value": "TRANSPHARM"}
                ],
                "allocate": [{"account": "Purchases – Dispensary", "percent": 100}],
                "contact": "Primary Pharma Suppliers"
            },
            {
                "name": "Frontshop suppliers → Purchases (Frontshop)",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "UNICORN"},
                    {"field": "description", "operator": "contains", "value": "COSMETICS"},
                    {"field": "description", "operator": "contains", "value": "TOILETRIES"},
                    {"field": "description", "operator": "contains", "value": "OTC"}
                ],
                "allocate": [{"account": "Purchases – Front Shop", "percent": 100}],
                "contact": "Frontshop Suppliers"
            },
            {
                "name": "SARS VAT",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "SARS"},
                    {"field": "description", "operator": "contains", "value": "VAT"}
                ],
                "allocate": [{"account": "VAT Payable (Settlement)", "percent": 100}],
                "contact": "SARS"
            },
            {
                "name": "SARS PAYE/UIF/SDL",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "PAYE"},
                    {"field": "description", "operator": "contains", "value": "UIF"},
                    {"field": "description", "operator": "contains", "value": "SDL"}
                ],
                "allocate": [{"account": "Payroll Taxes Payable", "percent": 100}],
                "contact": "SARS Payroll"
            },
            {
                "name": "Payroll runs (Sage/SimplePay) → Wages & Salaries",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "SAGE"},
                    {"field": "description", "operator": "contains", "value": "SIMPLEPAY"},
                    {"field": "description", "operator": "contains", "value": "PAYROLL"}
                ],
                "allocate": [{"account": "Wages & Salaries", "percent": 100}],
                "contact": "Payroll"
            },
            {
                "name": "Staff reimbursements → Staff Costs",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "REIMBURSE"},
                    {"field": "description", "operator": "contains", "value": "REFUND STAFF"}
                ],
                "allocate": [{"account": "Staff Costs", "percent": 100}]
            },
            {
                "name": "Municipality/Eskom → Utilities",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "MUNICIPAL"},
                    {"field": "description", "operator": "contains", "value": "ESKOM"},
                    {"field": "description", "operator": "contains", "value": "PREPAID ELECT"}
                ],
                "allocate": [{"account": "Utilities – Electricity/Water", "percent": 100}]
            },
            {
                "name": "Internet/Voice → Telco",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "VODACOM"},
                    {"field": "description", "operator": "contains", "value": "MTN"},
                    {"field": "description", "operator": "contains", "value": "TELKOM"},
                    {"field": "description", "operator": "contains", "value": "AFRIHOST"},
                    {"field": "description", "operator": "contains", "value": "RAIN"}
                ],
                "allocate": [{"account": "Telephone & Internet", "percent": 100}]
            },
            {
                "name": "Rent / Lease",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "RENT"},
                    {"field": "description", "operator": "contains", "value": "LEASE"}
                ],
                "allocate": [{"account": "Rent – Premises", "percent": 100}]
            },
            {
                "name": "Insurance premiums",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "OUTSURANCE"},
                    {"field": "description", "operator": "contains", "value": "SANTAM"},
                    {"field": "description", "operator": "contains", "value": "HOLLARD"},
                    {"field": "description", "operator": "contains", "value": "INSURANCE"}
                ],
                "allocate": [{"account": "Insurance Expense", "percent": 100}]
            },
            {
                "name": "Security/Armed response",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "ADT"},
                    {"field": "description", "operator": "contains", "value": "Fidelity"},
                    {"field": "description", "operator": "contains", "value": "ARMED RESPONSE"}
                ],
                "allocate": [{"account": "Security", "percent": 100}]
            },
            {
                "name": "Fuel & vehicle",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "ENGEN"},
                    {"field": "description", "operator": "contains", "value": "SHELL"},
                    {"field": "description", "operator": "contains", "value": "TOTAL"},
                    {"field": "description", "operator": "contains", "value": "BP"},
                    {"field": "description", "operator": "contains", "value": "SASOL"}
                ],
                "allocate": [{"account": "Motor Vehicle – Fuel", "percent": 100}]
            },
            {
                "name": "Courier / Post",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "RAM"},
                    {"field": "description", "operator": "contains", "value": "DAWN WING"},
                    {"field": "description", "operator": "contains", "value": "PUDO"},
                    {"field": "description", "operator": "contains", "value": "ARAMEX"},
                    {"field": "description", "operator": "contains", "value": "POSTNET"}
                ],
                "allocate": [{"account": "Courier & Postage", "percent": 100}]
            },
            {
                "name": "Software subscriptions",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "MICROSOFT"},
                    {"field": "description", "operator": "contains", "value": "ADOBE"},
                    {"field": "description", "operator": "contains", "value": "GOOGLE"},
                    {"field": "description", "operator": "contains", "value": "APPLE"},
                    {"field": "description", "operator": "contains", "value": "ZOOM"},
                    {"field": "description", "operator": "contains", "value": "IDEXIS"}
                ],
                "allocate": [{"account": "Software & IT Services", "percent": 100}]
            },
            {
                "name": "Bank charges",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "BANK CHARGES"},
                    {"field": "description", "operator": "contains", "value": "SERVICE FEE"},
                    {"field": "description", "operator": "contains", "value": "MONTHLY FEE"},
                    {"field": "description", "operator": "contains", "value": "TRANSACTION FEE"}
                ],
                "allocate": [{"account": "Bank Charges", "percent": 100}]
            },
            {
                "name": "Interest paid",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "INTEREST DEBIT"},
                    {"field": "description", "operator": "contains", "value": "OD INTEREST"}
                ],
                "allocate": [{"account": "Interest Paid", "percent": 100}]
            },
            {
                "name": "Interest received",
                "type": "receive",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "INTEREST CREDIT"},
                    {"field": "description", "operator": "contains", "value": "INT CR"}
                ],
                "allocate": [{"account": "Interest Received", "percent": 100}]
            },
            {
                "name": "Cash withdrawals → Petty cash",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "CASH WITHDRAWAL"},
                    {"field": "description", "operator": "contains", "value": "ATM WITHDRAWAL"}
                ],
                "allocate": [{"account": "Petty Cash", "percent": 100}]
            },
            {
                "name": "Cash deposits / Autosafe → Takings Clearing",
                "type": "receive",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "CASH DEPOSIT"},
                    {"field": "description", "operator": "contains", "value": "AUTOSAFE"}
                ],
                "allocate": [{"account": "Takings Clearing", "percent": 100}]
            },
            {
                "name": "Airtime / Vouchers",
                "type": "spend",
                "conditions_any": [
                    {"field": "description", "operator": "contains", "value": "AIRTIME"},
                    {"field": "description", "operator": "contains", "value": "VOUCHER"}
                ],
                "allocate": [{"account": "Cost of Sales – Vouchers/Airtime", "percent": 100}]
            }
        ]
    }
    
    pharmacy_id = 1  # Default pharmacy ID
    
    print("🔍 Loading accounts via API...")
    accounts_map = get_all_accounts()
    print(f"✅ Found {len(accounts_map)} accounts")
    
    # Print account names for debugging
    print("\n📋 Available accounts:")
    for name in sorted(accounts_map.keys()):
        print(f"  - {name}")
    
    print(f"\n📝 Processing {len(rules_json['rules'])} rules...\n")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for rule_json in rules_json['rules']:
        # Use priority from rule if specified, otherwise use order
        if 'priority' not in rule_json:
            rule_json['priority'] = 100  # Default priority
        
        api_rule = convert_rule_format(rule_json, accounts_map, pharmacy_id)
        
        if api_rule is None:
            skipped_count += 1
            continue
        
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
