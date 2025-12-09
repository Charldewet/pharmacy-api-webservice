#!/usr/bin/env python3
"""
Test script to parse the example transactions.csv file and show totals.
"""

import sys
import os

# Add parent directory to path to import pharma_api modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pharma_api.app.services.bank_csv_parser import BankCsvParser

def main():
    csv_file_path = os.path.join(os.path.dirname(__file__), '..', 'statementsExample', 'transactions.csv')
    
    if not os.path.exists(csv_file_path):
        print(f"Error: File not found: {csv_file_path}")
        return 1
    
    # Read file content
    with open(csv_file_path, 'rb') as f:
        file_content = f.read()
    
    # Parse CSV
    print("Parsing transactions.csv...")
    try:
        parse_result = BankCsvParser.parse(file_content)
        
        print(f"\n{'='*60}")
        print("PARSE RESULTS")
        print(f"{'='*60}")
        print(f"\nSummary:")
        print(f"  Transaction count: {parse_result.summary['transaction_count']}")
        print(f"  Total IN:  R {parse_result.summary['total_in']:,.2f}")
        print(f"  Total OUT: R {parse_result.summary['total_out']:,.2f}")
        print(f"  Net:       R {parse_result.summary['total_in'] + parse_result.summary['total_out']:,.2f}")
        print(f"\nDate range:")
        print(f"  From: {parse_result.summary['min_date']}")
        print(f"  To:   {parse_result.summary['max_date']}")
        
        print(f"\nErrors: {len(parse_result.errors)}")
        if parse_result.errors:
            print("\nFirst 5 errors:")
            for error in parse_result.errors[:5]:
                print(f"  Row {error.row_number}: {error.error}")
        
        # Show sample transactions
        print(f"\n{'='*60}")
        print("SAMPLE TRANSACTIONS (first 10)")
        print(f"{'='*60}")
        for row in parse_result.rows[:10]:
            amount_str = f"R {row.amount:,.2f}" if row.amount >= 0 else f"R {row.amount:,.2f}"
            print(f"{row.date} | {amount_str:>15} | {row.description[:50]}")
        
        return 0
        
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

