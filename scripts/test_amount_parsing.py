#!/usr/bin/env python3
"""
Test script to verify amount parsing preserves correct signs
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pharma_api.app.services.bank_parsers import StandardBankParser, FNBParser, ABSAParser
from decimal import Decimal

def test_amount_parsing():
    """Test amount parsing with positive and negative values"""
    
    # Test cases from the example CSV
    test_cases = [
        # (description, amount_str, expected_sign)
        ("Negative debit", "-341.40", "negative"),
        ("Positive credit", "18796.65", "positive"),
        ("Another positive credit", "15697.15", "positive"),
        ("Another negative debit", "-110.00", "negative"),
        ("Large positive", "300000.00", "positive"),
        ("Large negative", "-700000.00", "negative"),
    ]
    
    parsers = [
        ("Standard Bank", StandardBankParser()),
        ("FNB", FNBParser()),
        ("ABSA", ABSAParser()),
    ]
    
    print("Testing amount parsing with positive and negative values:\n")
    
    all_passed = True
    
    for parser_name, parser in parsers:
        print(f"=== {parser_name} Parser ===")
        for desc, amount_str, expected_sign in test_cases:
            # Create a mock row with single Amount field (like the CSV)
            row = {"Date": "29/11/2025", "Description": desc, "Amount": amount_str}
            parsed = parser._parse_amount(row)
            
            if parsed is None:
                print(f"  ✗ '{amount_str}' -> None (FAILED)")
                all_passed = False
                continue
            
            # Check sign
            is_positive = parsed > 0
            is_negative = parsed < 0
            
            if expected_sign == "positive" and is_positive:
                status = "✓"
            elif expected_sign == "negative" and is_negative:
                status = "✓"
            else:
                status = "✗"
                all_passed = False
            
            sign_str = "positive" if is_positive else "negative"
            print(f"  {status} '{amount_str}' -> {parsed} ({sign_str})")
        print()
    
    # Test with example CSV rows
    print("=== Testing with Example CSV Rows ===")
    example_rows = [
        {
            "Date": "29/11/2025",
            "Description": "SERVICE FEE ACC   301666148",
            "Amount": "-341.40"
        },
        {
            "Date": "29/11/2025",
            "Description": "CREDIT CARD EFTPOS SETTLEMENT DR EFTPOS 1OB  1  0000304515587",
            "Amount": "18796.65"
        },
        {
            "Date": "29/11/2025",
            "Description": "CREDIT CARD EFTPOS SETTLEMENT DR EFTPOS 1OB  0  0000234515587",
            "Amount": "15697.15"
        },
        {
            "Date": "29/11/2025",
            "Description": "IB PAYMENT TO Khumbula Trading Khumbulatrad",
            "Amount": "-13955.11"
        },
    ]
    
    parser = StandardBankParser()
    for i, row in enumerate(example_rows, 1):
        result = parser.parse_row(row, i)
        amount = result.amount
        sign = "positive" if amount > 0 else "negative"
        status = "✓" if not result.error else "✗"
        
        print(f"  Row {i}: {status} Amount={amount} ({sign}) - {row['Description'][:50]}")
        
        if result.error:
            print(f"    Error: {result.error}")
            all_passed = False
        elif (amount > 0 and float(row['Amount']) < 0) or (amount < 0 and float(row['Amount']) > 0):
            print(f"    ✗ Sign mismatch! Expected {row['Amount']} but got {amount}")
            all_passed = False
    
    print()
    if all_passed:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False

if __name__ == "__main__":
    success = test_amount_parsing()
    sys.exit(0 if success else 1)

