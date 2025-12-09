"""
Bank Statement Importer
Handles importing parsed bank statements into the database.
Based on Ruby implementation for consistency.
"""

import hashlib
from typing import Optional, Tuple, List
from datetime import date
from decimal import Decimal

from .bank_csv_parser import BankCsvParser, ParseResult, ParsedRow


class SuspectedDuplicate:
    """Represents a transaction that might be a duplicate"""
    def __init__(self, row_number: int, date: date, description: str, amount: Decimal,
                 reference: Optional[str], match_reason: str, existing_transaction_id: Optional[int] = None,
                 existing_date: Optional[date] = None, existing_description: Optional[str] = None):
        self.row_number = row_number
        self.date = date
        self.description = description
        self.amount = amount
        self.reference = reference
        self.match_reason = match_reason
        self.existing_transaction_id = existing_transaction_id
        self.existing_date = existing_date
        self.existing_description = existing_description


class ImportResult:
    """Result of importing a bank statement"""
    def __init__(self, bank_import_batch_id: int, transactions_inserted: int,
                 transactions_skipped_as_duplicates: int, errors: list, summary: dict,
                 suspected_duplicates: list = None):
        self.bank_import_batch_id = bank_import_batch_id
        self.transactions_inserted = transactions_inserted
        self.transactions_skipped_as_duplicates = transactions_skipped_as_duplicates
        self.errors = errors
        self.summary = summary
        self.suspected_duplicates = suspected_duplicates or []


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
            inserted = 0
            skipped = 0
            insert_errors = []
            
            # Duplicate detection - less strict: only skip if external_id matches or very high confidence
            suspected_duplicates = []
            exact_duplicates = set()
            
            if self.skip_duplicates and parse_result.rows:
                # Check for duplicates - be less strict
                # Only skip if we have a very high confidence match (external_id or exact match)
                for row in parse_result.rows:
                    external_id = self._build_external_id(row)
                    
                    # Check for duplicate by external_id first (highest confidence)
                    external_id_match = self._check_external_id_duplicate(cur, external_id)
                    if external_id_match:
                        exact_duplicates.add((row.date, float(row.amount), row.description))
                        skipped += 1
                        suspected_duplicates.append(SuspectedDuplicate(
                            row_number=row.row_number,
                            date=row.date,
                            description=row.description,
                            amount=row.amount,
                            reference=row.reference,
                            match_reason="High confidence: Same external_id (deterministic hash)",
                            existing_transaction_id=external_id_match.get('id'),
                            existing_date=external_id_match.get('date'),
                            existing_description=external_id_match.get('description')
                        ))
                        continue
                    
                    # Check for exact duplicate (date + amount + description) - medium confidence
                    # Only skip if it's from a different import batch (not same file re-imported)
                    exact_match = self._check_exact_duplicate(cur, row)
                    if exact_match:
                        existing_batch_id = exact_match.get('bank_import_batch_id')
                        # Skip if it exists and is from a different batch (avoid re-importing same file)
                        # But be lenient - only skip if we're very confident it's a duplicate
                        if existing_batch_id:
                            exact_duplicates.add((row.date, float(row.amount), row.description))
                            skipped += 1
                            suspected_duplicates.append(SuspectedDuplicate(
                                row_number=row.row_number,
                                date=row.date,
                                description=row.description,
                                amount=row.amount,
                                reference=row.reference,
                                match_reason="Exact match: Same date, amount, and description (from previous import)",
                                existing_transaction_id=exact_match.get('id'),
                                existing_date=exact_match.get('date'),
                                existing_description=exact_match.get('description')
                            ))
                            continue
                    
                    # Check for similar match (date + amount only) - low confidence, don't skip
                    similar_match = self._check_similar_duplicate(cur, row)
                    if similar_match:
                        # Flag as suspected but don't skip - let user decide
                        suspected_duplicates.append(SuspectedDuplicate(
                            row_number=row.row_number,
                            date=row.date,
                            description=row.description,
                            amount=row.amount,
                            reference=row.reference,
                            match_reason=f"Similar match: Same date ({row.date}) and amount ({row.amount}), but description differs",
                            existing_transaction_id=similar_match.get('id'),
                            existing_date=similar_match.get('date'),
                            existing_description=similar_match.get('description')
                        ))
                
                logger.info(f"Duplicate check: {len(exact_duplicates)} exact duplicates skipped, {len(suspected_duplicates)} suspected duplicates found")
            
            # Create import batch AFTER duplicate check (so we know how many will be inserted)
            batch_id = self._create_import_batch(cur, parse_result.summary)
            
            # Prepare transactions for batch insert
            transactions_to_insert = []
            for row in parse_result.rows:
                key = (row.date, float(row.amount), row.description)
                
                # Only skip high-confidence duplicates
                if self.skip_duplicates and key in exact_duplicates:
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
                summary=parse_result.summary,
                suspected_duplicates=suspected_duplicates
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
    
    def _check_external_id_duplicate(self, cur, external_id: str) -> Optional[dict]:
        """
        Check for duplicate by external_id (highest confidence).
        Returns existing transaction info if found, None otherwise.
        """
        if not external_id:
            return None
        try:
            cur.execute("""
                SELECT id, date, description, amount, bank_import_batch_id
                FROM pharma.bank_transactions
                WHERE bank_account_id = %s
                  AND external_id = %s
                LIMIT 1
            """, (self.bank_account_id, external_id))
            result = cur.fetchone()
            return dict(result) if result else None
        except Exception:
            return None
    
    def _check_exact_duplicate(self, cur, row: ParsedRow) -> Optional[dict]:
        """
        Check for exact duplicate: same date + amount + description.
        Returns existing transaction info if found, None otherwise.
        """
        try:
            cur.execute("""
                SELECT id, date, description, amount, bank_import_batch_id
                FROM pharma.bank_transactions
                WHERE bank_account_id = %s
                  AND date = %s
                  AND amount = %s
                  AND description = %s
                LIMIT 1
            """, (
                self.bank_account_id,
                row.date,
                float(row.amount),
                row.description
            ))
            result = cur.fetchone()
            return dict(result) if result else None
        except Exception:
            return None
    
    def _check_similar_duplicate(self, cur, row: ParsedRow) -> Optional[dict]:
        """
        Check for similar duplicate: same date + amount (less strict).
        This catches cases where description might vary slightly.
        Returns existing transaction info if found, None otherwise.
        """
        try:
            cur.execute("""
                SELECT id, date, description, amount, bank_import_batch_id
                FROM pharma.bank_transactions
                WHERE bank_account_id = %s
                  AND date = %s
                  AND amount = %s
                LIMIT 1
            """, (
                self.bank_account_id,
                row.date,
                float(row.amount)
            ))
            result = cur.fetchone()
            return dict(result) if result else None
        except Exception:
            return None
    
    def _build_external_id(self, row: ParsedRow) -> Optional[str]:
        """
        Build a deterministic external_id from transaction data.
        This creates a hash that can be used for duplicate detection.
        """
        # Create a deterministic hash from transaction data
        hash_input = f"{self.bank_account_id}|{row.date}|{row.amount}|{row.description}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

