#!/usr/bin/env python3
"""
Debug script to understand how summary is calculated vs frontend expectations.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pharma_api.app.services.bank_csv_parser import BankCsvParser

def main():
    csv_file_path = os.path.join(os.path.dirname(__file__), '..', 'statementsExample', 'transactions.csv')
    
    with open(csv_file_path, 'rb') as f:
        file_content = f.read()
    
    parse_result = BankCsvParser.parse(file_content)
    
    # Current calculation (what parser does)
    total_in_current = parse_result.summary['total_in']
    total_out_current = parse_result.summary['total_out']
    
    # Alternative calculation - maybe frontend expects absolute values?
    total_in_abs = sum(abs(row.amount) for row in parse_result.rows if row.amount > 0)
    total_out_abs = sum(abs(row.amount) for row in parse_result.rows if row.amount < 0)
    
    # Or maybe frontend treats all positive as IN and all negative as OUT (absolute)?
    total_in_alt = sum(abs(amt) for amt in [row.amount for row in parse_result.rows] if amt > 0)
    total_out_alt = sum(abs(amt) for amt in [row.amount for row in parse_result.rows] if amt < 0)
    
    # Check if there's a pattern with DR/CR in descriptions
    dr_transactions = [row for row in parse_result.rows if 'DR' in row.description.upper()]
    cr_transactions = [row for row in parse_result.rows if 'CR' in row.description.upper()]
    
    dr_total = sum(row.amount for row in dr_transactions)
    cr_total = sum(row.amount for row in cr_transactions)
    
    print("="*70)
    print("SUMMARY CALCULATION ANALYSIS")
    print("="*70)
    print(f"\nCurrent Parser Calculation:")
    print(f"  Total IN (amounts > 0):  R {total_in_current:,.2f}")
    print(f"  Total OUT (amounts < 0): R {total_out_current:,.2f}")
    
    print(f"\nAlternative Calculation (absolute values):")
    print(f"  Total IN (abs of amounts > 0):  R {total_in_abs:,.2f}")
    print(f"  Total OUT (abs of amounts < 0): R {total_out_abs:,.2f}")
    
    print(f"\nFrontend Expected (from image):")
    print(f"  Total IN:  R 22,299,468.90")
    print(f"  Total OUT: R 8,327,040.05")
    
    print(f"\nTransaction Analysis:")
    print(f"  Total transactions: {len(parse_result.rows)}")
    print(f"  Positive amounts: {sum(1 for row in parse_result.rows if row.amount > 0)}")
    print(f"  Negative amounts: {sum(1 for row in parse_result.rows if row.amount < 0)}")
    print(f"  Sum of all amounts: R {sum(row.amount for row in parse_result.rows):,.2f}")
    
    print(f"\nDR/CR Analysis:")
    print(f"  Transactions with 'DR': {len(dr_transactions)}")
    print(f"  Transactions with 'CR': {len(cr_transactions)}")
    print(f"  DR total: R {dr_total:,.2f}")
    print(f"  CR total: R {cr_total:,.2f}")
    
    # Check if frontend might be summing all positive and all negative differently
    all_positive_sum = sum(row.amount for row in parse_result.rows if row.amount > 0)
    all_negative_sum = sum(row.amount for row in parse_result.rows if row.amount < 0)
    
    print(f"\nAll Positive Sum: R {all_positive_sum:,.2f}")
    print(f"All Negative Sum: R {all_negative_sum:,.2f}")
    print(f"All Negative Sum (abs): R {abs(all_negative_sum):,.2f}")
    
    # Check if frontend expects: IN = all positive, OUT = absolute of all negative
    all_positive_sum_float = float(all_positive_sum)
    all_negative_sum_abs_float = abs(float(all_negative_sum))
    
    if abs(all_positive_sum_float - 22399468.90) < 1000:
        print(f"\n*** MATCH FOUND: Frontend IN = sum of all positive amounts")
    if abs(all_negative_sum_abs_float - 8327040.05) < 1000:
        print(f"*** MATCH FOUND: Frontend OUT = absolute of sum of all negative amounts")
    
    # Check if maybe frontend is summing DR and CR separately?
    print(f"\nChecking DR vs CR patterns:")
    dr_positive = sum(row.amount for row in dr_transactions if row.amount > 0)
    dr_negative = sum(row.amount for row in dr_transactions if row.amount < 0)
    cr_positive = sum(row.amount for row in cr_transactions if row.amount > 0)
    cr_negative = sum(row.amount for row in cr_transactions if row.amount < 0)
    
    print(f"  DR positive: R {dr_positive:,.2f}")
    print(f"  DR negative: R {dr_negative:,.2f}")
    print(f"  CR positive: R {cr_positive:,.2f}")
    print(f"  CR negative: R {cr_negative:,.2f}")
    
    # Maybe frontend calculates: IN = DR amounts, OUT = CR amounts?
    print(f"\nIf IN = DR total and OUT = CR total:")
    print(f"  IN:  R {dr_total:,.2f}")
    print(f"  OUT: R {cr_total:,.2f}")

if __name__ == '__main__':
    main()

