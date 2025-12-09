#!/usr/bin/env python3
"""
Check bank transactions uploaded for Reitz Pharmacy.
Reitz Pharmacy has pharmacy_id = 1
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.conn import get_conn

def format_amount(amount: Decimal) -> str:
    """Format amount with currency symbol"""
    if amount is None:
        return "N/A"
    return f"R {amount:,.2f}"

def format_date(d: datetime) -> str:
    """Format date"""
    if d is None:
        return "N/A"
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d")
    return str(d)

def main():
    pharmacy_id = 1  # Reitz Pharmacy
    
    print("=" * 80)
    print(f"BANK TRANSACTIONS FOR REITZ PHARMACY (pharmacy_id = {pharmacy_id})")
    print("=" * 80)
    print()
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # First, check if pharmacy exists
            cur.execute("""
                SELECT pharmacy_id, name 
                FROM pharma.pharmacies 
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            
            pharmacy = cur.fetchone()
            if not pharmacy:
                print(f"❌ Pharmacy with ID {pharmacy_id} not found!")
                return
            
            print(f"Pharmacy: {pharmacy['name']}")
            print()
            
            # Get bank accounts for this pharmacy
            cur.execute("""
                SELECT id, name, bank_name, account_number, currency, is_active
                FROM pharma.bank_accounts
                WHERE pharmacy_id = %s
                ORDER BY created_at DESC
            """, (pharmacy_id,))
            
            bank_accounts = cur.fetchall()
            
            if not bank_accounts:
                print("⚠️  No bank accounts found for Reitz Pharmacy")
                return
            
            print(f"Bank Accounts: {len(bank_accounts)}")
            for acc in bank_accounts:
                status = "Active" if acc['is_active'] else "Inactive"
                print(f"  - {acc['name']} ({acc['bank_name']}) - {status}")
            print()
            
            # Get import batches
            cur.execute("""
                SELECT 
                    bib.id,
                    bib.bank_account_id,
                    ba.name as account_name,
                    ba.bank_name,
                    bib.period_start,
                    bib.period_end,
                    bib.file_name,
                    bib.uploaded_at,
                    bib.status,
                    bib.notes,
                    COUNT(bt.id) as transaction_count
                FROM pharma.bank_import_batches bib
                JOIN pharma.bank_accounts ba ON bib.bank_account_id = ba.id
                LEFT JOIN pharma.bank_transactions bt ON bt.bank_import_batch_id = bib.id
                WHERE bib.pharmacy_id = %s
                GROUP BY bib.id, ba.name, ba.bank_name
                ORDER BY bib.uploaded_at DESC
            """, (pharmacy_id,))
            
            batches = cur.fetchall()
            
            print(f"Import Batches: {len(batches)}")
            print()
            
            if not batches:
                print("⚠️  No bank import batches found for Reitz Pharmacy")
                return
            
            # Display batches summary
            for batch in batches:
                print(f"Batch ID: {batch['id']}")
                print(f"  Account: {batch['account_name']} ({batch['bank_name']})")
                print(f"  File: {batch['file_name']}")
                print(f"  Period: {format_date(batch['period_start'])} to {format_date(batch['period_end'])}")
                print(f"  Uploaded: {batch['uploaded_at']}")
                print(f"  Status: {batch['status']}")
                print(f"  Transactions: {batch['transaction_count']}")
                if batch['notes']:
                    print(f"  Notes: {batch['notes']}")
                print()
            
            # Get all transactions
            cur.execute("""
                SELECT 
                    bt.id,
                    bt.bank_import_batch_id,
                    bt.bank_account_id,
                    ba.name as account_name,
                    ba.bank_name,
                    bt.date,
                    bt.description,
                    bt.raw_description,
                    bt.reference,
                    bt.amount,
                    bt.balance,
                    bt.external_id,
                    bt.created_at
                FROM pharma.bank_transactions bt
                JOIN pharma.bank_accounts ba ON bt.bank_account_id = ba.id
                WHERE bt.pharmacy_id = %s
                ORDER BY bt.date DESC, bt.id DESC
            """, (pharmacy_id,))
            
            transactions = cur.fetchall()
            
            print("=" * 80)
            print(f"TOTAL TRANSACTIONS: {len(transactions)}")
            print("=" * 80)
            print()
            
            if not transactions:
                print("⚠️  No bank transactions found for Reitz Pharmacy")
                return
            
            # Calculate summary statistics
            total_amount = sum(float(t['amount']) for t in transactions)
            positive_amounts = [float(t['amount']) for t in transactions if float(t['amount']) > 0]
            negative_amounts = [float(t['amount']) for t in transactions if float(t['amount']) < 0]
            
            print("SUMMARY:")
            print(f"  Total Transactions: {len(transactions)}")
            print(f"  Net Amount: {format_amount(Decimal(str(total_amount)))}")
            print(f"  Credits (positive): {len(positive_amounts)} transactions, Total: {format_amount(Decimal(str(sum(positive_amounts))))}")
            print(f"  Debits (negative): {len(negative_amounts)} transactions, Total: {format_amount(Decimal(str(sum(negative_amounts))))}")
            print()
            
            # Group by date range
            if transactions:
                dates = [t['date'] for t in transactions if t['date']]
                if dates:
                    min_date = min(dates)
                    max_date = max(dates)
                    print(f"Date Range: {format_date(min_date)} to {format_date(max_date)}")
                    print()
            
            # Show first 20 transactions
            print("=" * 80)
            print("RECENT TRANSACTIONS (showing first 20):")
            print("=" * 80)
            print()
            
            for i, txn in enumerate(transactions[:20], 1):
                print(f"{i}. Date: {format_date(txn['date'])}")
                print(f"   Account: {txn['account_name']} ({txn['bank_name']})")
                print(f"   Amount: {format_amount(txn['amount'])}")
                print(f"   Description: {txn['description']}")
                if txn['raw_description'] and txn['raw_description'] != txn['description']:
                    print(f"   Raw Description: {txn['raw_description']}")
                if txn['reference']:
                    print(f"   Reference: {txn['reference']}")
                if txn['balance']:
                    print(f"   Balance: {format_amount(txn['balance'])}")
                print(f"   Batch ID: {txn['bank_import_batch_id']}")
                print()
            
            if len(transactions) > 20:
                print(f"... and {len(transactions) - 20} more transactions")
                print()

if __name__ == "__main__":
    main()

