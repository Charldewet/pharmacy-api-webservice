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
        import logging
        import json
        logger = logging.getLogger(__name__)
        
        # Parse CSV
        parse_result = BankCsvParser.parse(self.file_content)
        
        with self.conn.cursor() as cur:
            # Create import batch
            batch_id = self._create_import_batch(cur, parse_result.summary)
            
            inserted = 0
            skipped = 0
            insert_errors = []
            
            # Batch duplicate detection for better performance
            if self.skip_duplicates and parse_result.rows:
                # Collect all transaction keys to check
                transaction_keys = [
                    (row.date, float(row.amount), row.description)
                    for row in parse_result.rows
                ]
                
                # Bulk check for duplicates
                existing_keys = self._bulk_check_duplicates(cur, transaction_keys)
                logger.info(f"Duplicate check: {len(existing_keys)} duplicates found out of {len(transaction_keys)} transactions")
            else:
                existing_keys = set()
            
            # Prepare transactions for batch insert
            transactions_to_insert = []
            for row in parse_result.rows:
                key = (row.date, float(row.amount), row.description)
                
                if self.skip_duplicates and key in existing_keys:
                    skipped += 1
                    continue
                
                # Add to insert list
                
                # Prepare transaction data
                external_id = self._build_external_id(row)
                amount_value = float(row.amount) if row.amount is not None else None
                balance_value = float(row.balance) if row.balance is not None else None
                raw_data_json = json.dumps(row.raw_data) if row.raw_data else None
                description = row.description or ""
                raw_description = row.raw_description or description
                
                transactions_to_insert.append((
                    batch_id,
                    self.bank_account_id,
                    self.pharmacy_id,
                    row.date,
                    description,
                    raw_description,
                    row.reference,
                    amount_value,
                    balance_value,
                    raw_data_json,
                    external_id
                ))
            
            # Batch insert transactions
            logger.info(f"Prepared {len(transactions_to_insert)} transactions for insertion (skipped {skipped} duplicates)")
            
            if transactions_to_insert:
                BATCH_SIZE = 500
                for i in range(0, len(transactions_to_insert), BATCH_SIZE):
                    chunk = transactions_to_insert[i:i + BATCH_SIZE]
                    try:
                        cur.executemany("""
                            INSERT INTO pharma.bank_transactions
                            (bank_import_batch_id, bank_account_id, pharmacy_id, date, description,
                             raw_description, reference, amount, balance, raw_data, external_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, chunk)
                        inserted += len(chunk)
                        logger.info(f"Successfully inserted batch of {len(chunk)} transactions (total inserted: {inserted})")
                    except Exception as e:
                        # If batch insert fails, try individual inserts
                        logger.error(f"Batch insert failed for chunk {i//BATCH_SIZE + 1}: {str(e)}")
                        logger.warning(f"Falling back to individual inserts for this chunk")
                        for data in chunk:
                            try:
                                cur.execute("""
                                    INSERT INTO pharma.bank_transactions
                                    (bank_import_batch_id, bank_account_id, pharmacy_id, date, description,
                                     raw_description, reference, amount, balance, raw_data, external_id)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, data)
                                inserted += 1
                            except Exception as insert_error:
                                logger.error(f"Failed to insert transaction: {str(insert_error)}")
                                skipped += 1
                                insert_errors.append(str(insert_error))
                                continue
            else:
                logger.warning(f"No transactions to insert! All {len(parse_result.rows)} transactions were skipped as duplicates or had errors.")
            
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
        
        # Ensure all values are properly formatted
        amount_value = float(row.amount) if row.amount is not None else None
        balance_value = float(row.balance) if row.balance is not None else None
        raw_data_json = json.dumps(row.raw_data) if row.raw_data else None
        
        # Ensure description is not None
        description = row.description or ""
        raw_description = row.raw_description or description
        
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
            description,
            raw_description,
            row.reference,
            amount_value,
            balance_value,
            raw_data_json,
            external_id
        ))
    
    def _bulk_check_duplicates(self, cur, transaction_keys: list) -> set:
        """
        Bulk check for duplicate transactions.
        Returns a set of (date, amount, description) tuples that already exist.
        """
        if not transaction_keys:
            return set()
        
        # Use a temporary table for efficient bulk duplicate checking
        try:
            # Create temp table
            cur.execute("""
                CREATE TEMP TABLE temp_transaction_check (
                    check_date DATE,
                    check_amount DECIMAL,
                    check_description TEXT
                ) ON COMMIT DROP
            """)
            
            # Insert keys to check
            cur.executemany("""
                INSERT INTO temp_transaction_check (check_date, check_amount, check_description)
                VALUES (%s, %s, %s)
            """, transaction_keys)
            
            # Find existing duplicates
            cur.execute("""
                SELECT DISTINCT t.date, t.amount, t.description
                FROM pharma.bank_transactions t
                INNER JOIN temp_transaction_check tmp
                ON t.date = tmp.check_date
                AND t.amount = tmp.check_amount
                AND t.description = tmp.check_description
                WHERE t.bank_account_id = %s
            """, (self.bank_account_id,))
            
            existing = {(row['date'], row['amount'], row['description']) for row in cur.fetchall()}
            return existing
            
        except Exception as e:
            # If bulk check fails, fall back to individual checks
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Bulk duplicate check failed, using individual checks: {str(e)}")
            
            existing = set()
            for date_val, amount_val, desc_val in transaction_keys:
                try:
                    cur.execute("""
                        SELECT COUNT(*) as count
                        FROM pharma.bank_transactions
                        WHERE bank_account_id = %s
                          AND date = %s
                          AND amount = %s
                          AND description = %s
                    """, (self.bank_account_id, date_val, amount_val, desc_val))
                    result = cur.fetchone()
                    if result and result['count'] > 0:
                        existing.add((date_val, amount_val, desc_val))
                except Exception:
                    continue
            
            return existing
    
    def _build_external_id(self, row: ParsedRow) -> Optional[str]:
        """
        Build a deterministic external_id from transaction data.
        This creates a hash that can be used for duplicate detection.
        """
        # Create a deterministic hash from transaction data
        hash_input = f"{self.bank_account_id}|{row.date}|{row.amount}|{row.description}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

