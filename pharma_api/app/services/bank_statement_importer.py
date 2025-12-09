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
        """Main import logic - fastest path: no duplicate pre-check, bulk insert, ignore duplicates."""
        import logging
        import json
        logger = logging.getLogger(__name__)

        # Parse CSV (already fast)
        parse_result = BankCsvParser.parse(self.file_content)

        inserted = 0
        skipped = 0  # will count rows skipped by ON CONFLICT
        batch_id = None

        with self.conn.cursor() as cur:
            # Create import batch
            batch_id = self._create_import_batch(cur, parse_result.summary)

            # Prepare transactions for bulk insert
            transactions_to_insert = []
            for row in parse_result.rows:
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

            logger.info(f"Prepared {len(transactions_to_insert)} transactions for insertion")

            if transactions_to_insert:
                try:
                    insert_sql = """
                        INSERT INTO pharma.bank_transactions
                        (bank_import_batch_id, bank_account_id, pharmacy_id, date, description,
                         raw_description, reference, amount, balance, raw_data, external_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """
                    BATCH = 1000
                    for i in range(0, len(transactions_to_insert), BATCH):
                        chunk = transactions_to_insert[i:i+BATCH]
                        cur.executemany(insert_sql, chunk)
                        inserted_chunk = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
                        inserted += inserted_chunk
                    skipped = len(transactions_to_insert) - inserted
                    logger.info(f"Inserted {inserted} / {len(transactions_to_insert)} transactions (skipped {skipped} duplicates/conflicts)")
                except Exception as bulk_error:
                    logger.error(f"Bulk insert failed: {str(bulk_error)}")
                    raise
            else:
                logger.warning(f"No transactions to insert! File had {len(parse_result.rows)} rows.")

            # Insert parsing errors into bank_import_errors table (best-effort)
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
            suspected_duplicates=[]  # not computed in fast-path
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

    def _load_existing_transactions(self, cur, rows: List[ParsedRow]):
        """
        Bulk-load potential duplicates to avoid per-row queries.
        Returns three dictionaries keyed by:
        - external_id
        - (date, amount, description)
        - (date, amount)
        """
        existing_by_external = {}
        existing_by_exact = {}
        existing_by_similar = {}

        if not rows:
            return existing_by_external, existing_by_exact, existing_by_similar

        # Collect unique keys to keep payload small
        external_ids = []
        exact_keys = []
        similar_keys = []

        for row in rows:
            external_id = self._build_external_id(row)
            if external_id:
                external_ids.append(external_id)
            exact_keys.append((row.date, row.amount, row.description))
            similar_keys.append((row.date, row.amount))

        # Deduplicate while preserving order for array zip
        def _unique(seq):
            seen = set()
            out = []
            for item in seq:
                if item in seen:
                    continue
                seen.add(item)
                out.append(item)
            return out

        external_ids = _unique(external_ids)
        exact_keys = _unique(exact_keys)
        similar_keys = _unique(similar_keys)

        CHUNK = 1000

        # External ID lookup
        for i in range(0, len(external_ids), CHUNK):
            chunk = external_ids[i:i + CHUNK]
            cur.execute("""
                SELECT id, date, description, amount, bank_import_batch_id, external_id
                FROM pharma.bank_transactions
                WHERE bank_account_id = %s
                  AND external_id = ANY(%s)
            """, (self.bank_account_id, chunk))
            for row in cur.fetchall():
                existing_by_external[row['external_id']] = row

        # Exact match lookup (date, amount, description)
        for i in range(0, len(exact_keys), CHUNK):
            chunk = exact_keys[i:i + CHUNK]
            dates = [k[0] for k in chunk]
            amounts = [k[1] for k in chunk]
            descriptions = [k[2] for k in chunk]
            cur.execute("""
                WITH data(date, amount, description) AS (
                    SELECT * FROM unnest(%s::date[], %s::numeric[], %s::text[])
                )
                SELECT t.id, t.date, t.description, t.amount, t.bank_import_batch_id
                FROM data d
                JOIN pharma.bank_transactions t
                  ON t.bank_account_id = %s
                 AND t.date = d.date
                 AND t.amount = d.amount
                 AND t.description = d.description
            """, (dates, amounts, descriptions, self.bank_account_id))
            for row in cur.fetchall():
                key = (row['date'], Decimal(str(row['amount'])), row['description'])
                existing_by_exact[key] = row

        # Similar match lookup (date, amount)
        for i in range(0, len(similar_keys), CHUNK):
            chunk = similar_keys[i:i + CHUNK]
            dates = [k[0] for k in chunk]
            amounts = [k[1] for k in chunk]
            cur.execute("""
                WITH data(date, amount) AS (
                    SELECT * FROM unnest(%s::date[], %s::numeric[])
                )
                SELECT DISTINCT ON (t.date, t.amount)
                       t.id, t.date, t.description, t.amount, t.bank_import_batch_id
                FROM data d
                JOIN pharma.bank_transactions t
                  ON t.bank_account_id = %s
                 AND t.date = d.date
                 AND t.amount = d.amount
            """, (dates, amounts, self.bank_account_id))
            for row in cur.fetchall():
                key = (row['date'], Decimal(str(row['amount'])))
                existing_by_similar[key] = row

        return existing_by_external, existing_by_exact, existing_by_similar
