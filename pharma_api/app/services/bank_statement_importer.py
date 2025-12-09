"""
Bank Statement Importer
Handles importing parsed bank statements into the database.
Based on Ruby implementation for consistency.
"""

import hashlib
from typing import Optional, Tuple
from datetime import date
from decimal import Decimal

from .bank_csv_parser import BankCsvParser, ParseResult, ParsedRow


class ImportResult:
    """Result of importing a bank statement"""
    def __init__(self, bank_import_batch_id: int, transactions_inserted: int,
                 transactions_skipped_as_duplicates: int, errors: list, summary: dict):
        self.bank_import_batch_id = bank_import_batch_id
        self.transactions_inserted = transactions_inserted
        self.transactions_skipped_as_duplicates = transactions_skipped_as_duplicates
        self.errors = errors
        self.summary = summary


class BankStatementImporter:
    """Imports bank statements into the database"""
    
    @staticmethod
    def import_statement(conn, pharmacy_id: int, bank_account_id: int, 
                        file_content: bytes, file_name: str, 
                        uploaded_by_user_id: Optional[int] = None,
                        notes: Optional[str] = None,
                        skip_duplicates: bool = True) -> ImportResult:
        """
        Import a bank statement CSV file.
        
        Args:
            conn: Database connection (with cursor context manager)
            pharmacy_id: ID of the pharmacy
            bank_account_id: ID of the bank account
            file_content: Raw CSV file bytes
            file_name: Original filename
            uploaded_by_user_id: Optional user ID who uploaded
            notes: Optional notes about this import
            skip_duplicates: Whether to skip duplicate transactions
        
        Returns:
            ImportResult with import statistics
        """
        importer = BankStatementImporter(
            conn, pharmacy_id, bank_account_id, file_content, 
            file_name, uploaded_by_user_id, notes, skip_duplicates
        )
        return importer._import()
    
    def __init__(self, conn, pharmacy_id: int, bank_account_id: int,
                 file_content: bytes, file_name: str,
                 uploaded_by_user_id: Optional[int] = None,
                 notes: Optional[str] = None,
                 skip_duplicates: bool = True):
        self.conn = conn
        self.pharmacy_id = pharmacy_id
        self.bank_account_id = bank_account_id
        self.file_content = file_content
        self.file_name = file_name
        self.uploaded_by_user_id = uploaded_by_user_id
        self.notes = notes
        self.skip_duplicates = skip_duplicates
    
    def _import(self) -> ImportResult:
        """Main import logic"""
        # Parse CSV
        parse_result = BankCsvParser.parse(self.file_content)
        
        with self.conn.cursor() as cur:
            # Create import batch
            batch_id = self._create_import_batch(cur, parse_result.summary)
            
            inserted = 0
            skipped = 0
            
            # Process each row
            for row in parse_result.rows:
                if self.skip_duplicates and self._is_duplicate_transaction(cur, row):
                    skipped += 1
                    continue
                
                try:
                    self._create_bank_transaction(cur, batch_id, row)
                    inserted += 1
                except Exception as e:
                    # If insert fails, skip and continue
                    skipped += 1
                    continue
            
            # Insert parsing errors into bank_import_errors table
            import json
            for error in parse_result.errors:
                try:
                    cur.execute("""
                        INSERT INTO pharma.bank_import_errors
                        (bank_import_batch_id, row_number, raw_data, error_message)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        batch_id,
                        error.row_number,
                        json.dumps(error.raw_data) if error.raw_data else None,
                        error.error
                    ))
                except Exception:
                    # Log error but continue
                    continue
            
            # Update batch status
            cur.execute("""
                UPDATE pharma.bank_import_batches
                SET status = 'IMPORTED'
                WHERE id = %s
            """, (batch_id,))
            
            self.conn.commit()
            
            return ImportResult(
                bank_import_batch_id=batch_id,
                transactions_inserted=inserted,
                transactions_skipped_as_duplicates=skipped,
                errors=parse_result.errors,
                summary=parse_result.summary
            )
    
    def _create_import_batch(self, cur, summary: dict) -> int:
        """Create bank_import_batch record"""
        period_start = None
        period_end = None
        
        if summary.get('min_date'):
            period_start = date.fromisoformat(summary['min_date'])
        if summary.get('max_date'):
            period_end = date.fromisoformat(summary['max_date'])
        
        cur.execute("""
            INSERT INTO pharma.bank_import_batches
            (bank_account_id, pharmacy_id, period_start, period_end, file_name,
             uploaded_by_user_id, uploaded_at, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), 'IMPORTED', %s)
            RETURNING id
        """, (
            self.bank_account_id,
            self.pharmacy_id,
            period_start,
            period_end,
            self.file_name,
            self.uploaded_by_user_id,
            self.notes
        ))
        
        return cur.fetchone()['id']
    
    def _create_bank_transaction(self, cur, batch_id: int, row: ParsedRow):
        """Create bank_transaction record"""
        import json
        
        external_id = self._build_external_id(row)
        
        cur.execute("""
            INSERT INTO pharma.bank_transactions
            (bank_import_batch_id, bank_account_id, pharmacy_id, date, description,
             raw_description, reference, amount, balance, raw_data, external_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            batch_id,
            self.bank_account_id,
            self.pharmacy_id,
            row.date,
            row.description,
            row.raw_description,
            row.reference,
            float(row.amount),
            float(row.balance) if row.balance is not None else None,
            json.dumps(row.raw_data) if row.raw_data else None,
            external_id
        ))
    
    def _is_duplicate_transaction(self, cur, row: ParsedRow) -> bool:
        """
        Check if transaction is duplicate.
        Uses same date + amount + description on same bank account.
        """
        cur.execute("""
            SELECT COUNT(*) as count
            FROM pharma.bank_transactions
            WHERE bank_account_id = %s
              AND date = %s
              AND amount = %s
              AND description = %s
        """, (
            self.bank_account_id,
            row.date,
            float(row.amount),
            row.description
        ))
        
        result = cur.fetchone()
        return result['count'] > 0
    
    def _build_external_id(self, row: ParsedRow) -> Optional[str]:
        """
        Build a deterministic external_id from transaction data.
        This creates a hash that can be used for duplicate detection.
        """
        # Create a deterministic hash from transaction data
        hash_input = f"{self.bank_account_id}|{row.date}|{row.amount}|{row.description}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

