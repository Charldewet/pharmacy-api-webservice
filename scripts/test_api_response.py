#!/usr/bin/env python3
"""
Test what the API actually returns for the preview endpoint.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pharma_api.app.services.bank_csv_parser import BankCsvParser
from pharma_api.app.routers.bank_imports import _convert_summary_to_schema

def main():
    csv_file_path = os.path.join(os.path.dirname(__file__), '..', 'statementsExample', 'transactions.csv')
    
    with open(csv_file_path, 'rb') as f:
        file_content = f.read()
    
    parse_result = BankCsvParser.parse(file_content)
    summary_schema = _convert_summary_to_schema(parse_result.summary)
    
    print("="*70)
    print("API RESPONSE SUMMARY")
    print("="*70)
    print(f"\nSummary from parser:")
    print(json.dumps(parse_result.summary, indent=2))
    
    print(f"\nSummary schema (what API returns):")
    print(f"  transaction_count: {summary_schema.transaction_count}")
    print(f"  total_in: {summary_schema.total_in}")
    print(f"  total_out: {summary_schema.total_out}")
    print(f"  min_date: {summary_schema.min_date}")
    print(f"  max_date: {summary_schema.max_date}")
    
    print(f"\nFrontend Expected:")
    print(f"  Total IN:  R 22,299,468.90")
    print(f"  Total OUT: R 8,327,040.05")
    
    print(f"\nDifference:")
    print(f"  Total IN difference:  R {summary_schema.total_in - 22399468.90:,.2f}")
    print(f"  Total OUT difference: R {summary_schema.total_out - 8327040.05:,.2f}")
    
    # Check if frontend might be summing sample transactions
    sample_transactions = parse_result.rows[:20]
    sample_in = sum(row.amount for row in sample_transactions if row.amount > 0)
    sample_out = abs(sum(row.amount for row in sample_transactions if row.amount < 0))
    
    print(f"\nSample transactions (first 20):")
    print(f"  Sample IN:  R {sample_in:,.2f}")
    print(f"  Sample OUT: R {sample_out:,.2f}")

if __name__ == '__main__':
    main()

