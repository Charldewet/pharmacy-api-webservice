#!/usr/bin/env python3
"""
Test script to verify date parsing works with various date formats
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pharma_api.app.services.bank_parsers import StandardBankParser, FNBParser, ABSAParser

def test_date_parsing():
    """Test date parsing with various formats"""
    
    # Test dates from the example CSV
    test_dates = [
        "29/11/2025",
        "28/11/2025",
        "27/11/2025",
        "01/10/2025",
        "30/09/2025",
        "15/03/2025",
        "2025-03-15",
        "15-03-2025",
        "15 Mar 2025",
        "15 March 2025",
    ]
    
    parsers = [
        ("Standard Bank", StandardBankParser()),
        ("FNB", FNBParser()),
        ("ABSA", ABSAParser()),
    ]
    
    print("Testing date parsing with various formats:\n")
    
    for parser_name, parser in parsers:
        print(f"=== {parser_name} Parser ===")
        for date_str in test_dates:
            # Create a mock row
            row = {"Date": date_str, "Description": "Test", "Amount": "100.00"}
            parsed = parser._parse_date(row)
            status = "✓" if parsed else "✗"
            print(f"  {status} '{date_str}' -> {parsed}")
        print()
    
    # Test case-insensitive field matching
    print("=== Testing Case-Insensitive Field Matching ===")
    parser = StandardBankParser()
    test_rows = [
        {"date": "29/11/2025", "description": "Test", "amount": "100.00"},
        {"DATE": "29/11/2025", "DESCRIPTION": "Test", "AMOUNT": "100.00"},
        {"Date": "29/11/2025", "Description": "Test", "Amount": "100.00"},
    ]
    
    for i, row in enumerate(test_rows, 1):
        parsed_date = parser._parse_date(row)
        parsed_desc = parser._get_description(row)
        print(f"  Row {i}: date={parsed_date}, desc={parsed_desc}")
    
    print("\n=== Testing with Example CSV Format ===")
    # Simulate the exact format from transactions.csv
    example_row = {
        "Date": "29/11/2025",
        "Description": "SERVICE FEE ACC   301666148",
        "Amount": "-341.40"
    }
    
    parser = StandardBankParser()
    result = parser.parse_row(example_row, 1)
    
    print(f"Date: {result.date}")
    print(f"Description: {result.description}")
    print(f"Amount: {result.amount}")
    print(f"Error: {result.error}")
    
    if result.error:
        print(f"\n❌ ERROR: {result.error}")
        return False
    else:
        print("\n✓ Successfully parsed example row!")
        return True

if __name__ == "__main__":
    success = test_date_parsing()
    sys.exit(0 if success else 1)

