"""
Bank CSV Import API Router
Handles CSV upload, parsing, preview, and import confirmation.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import date, datetime
import json
from decimal import Decimal

from ..db import get_conn
from ..schemas import (
    ImportPreviewResponse, ImportSummary, ParsedTransaction, ImportError,
    ImportConfirmRequest, ImportConfirmResponse, BankImportBatch
)
from ..auth import require_api_key
from ..services.bank_parsers import parse_csv_file, BankParseResult

router = APIRouter(prefix="/bank-imports", tags=["bank-imports"])


def _compute_summary(valid_results: List[BankParseResult]) -> ImportSummary:
    """Compute summary statistics from parsed transactions"""
    if not valid_results:
        return ImportSummary(
            transaction_count=0,
            total_in=0.0,
            total_out=0.0,
            min_date=None,
            max_date=None
        )
    
    amounts = [float(r.amount) for r in valid_results if r.amount is not None]
    dates = [r.date for r in valid_results if r.date]
    
    total_in = sum(amt for amt in amounts if amt > 0)
    total_out = sum(amt for amt in amounts if amt < 0)
    
    min_date = min(dates) if dates else None
    max_date = max(dates) if dates else None
    
    return ImportSummary(
        transaction_count=len(valid_results),
        total_in=total_in,
        total_out=total_out,
        min_date=min_date,
        max_date=max_date
    )


def _convert_to_parsed_transaction(result: BankParseResult, row_number: int) -> ParsedTransaction:
    """Convert BankParseResult to ParsedTransaction schema"""
    return ParsedTransaction(
        row_number=row_number,
        date=result.date or "",
        description=result.description or "",
        reference=result.reference,
        amount=float(result.amount) if result.amount is not None else 0.0,
        balance=float(result.balance) if result.balance is not None else None
    )


def _convert_to_import_error(result: BankParseResult, row_number: int) -> ImportError:
    """Convert BankParseResult error to ImportError schema"""
    return ImportError(
        row_number=row_number,
        error=result.error or "Unknown error",
        raw_data=result.raw_data
    )


@router.post("/preview", response_model=ImportPreviewResponse, dependencies=[Depends(require_api_key)])
async def preview_bank_import(
    pharmacy_id: int = Form(...),
    bank_account_id: int = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload and preview a bank CSV file without saving to database.
    
    This endpoint:
    1. Validates pharmacy and bank account
    2. Parses the CSV file
    3. Returns preview with summary, sample transactions, and errors
    
    - **pharmacy_id**: ID of the pharmacy
    - **bank_account_id**: ID of the bank account
    - **file**: CSV file to import
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Validate pharmacy exists
        cur.execute(
            "SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s AND is_active = true",
            (pharmacy_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found or inactive")
        
        # Validate bank account exists and belongs to pharmacy
        cur.execute("""
            SELECT id, bank_name FROM pharma.bank_accounts
            WHERE id = %s AND pharmacy_id = %s AND is_active = true
        """, (bank_account_id, pharmacy_id))
        
        bank_account = cur.fetchone()
        if not bank_account:
            raise HTTPException(
                status_code=404,
                detail="Bank account not found, inactive, or does not belong to this pharmacy"
            )
        
        bank_name = bank_account['bank_name']
    
    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    if not file_content:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Parse CSV
    try:
        valid_results, error_results = parse_csv_file(file_content, bank_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing CSV: {str(e)}")
    
    # Compute summary
    summary = _compute_summary(valid_results)
    
    # Convert to response format
    # Sample first 20 transactions
    sample_transactions = [
        _convert_to_parsed_transaction(
            result,
            result.raw_data.get('_row_number', idx + 2) if result.raw_data else idx + 2
        )
        for idx, result in enumerate(valid_results[:20])
    ]
    
    errors = [
        _convert_to_import_error(
            result,
            result.raw_data.get('_row_number', idx + 2) if result.raw_data else idx + 2
        )
        for idx, result in enumerate(error_results)
    ]
    
    return ImportPreviewResponse(
        pharmacy_id=pharmacy_id,
        bank_account_id=bank_account_id,
        summary=summary,
        sample_transactions=sample_transactions,
        errors=errors
    )


@router.post("/confirm", response_model=ImportConfirmResponse, dependencies=[Depends(require_api_key)])
async def confirm_bank_import(
    pharmacy_id: int = Form(...),
    bank_account_id: int = Form(...),
    file_name: str = Form(...),
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    skip_duplicates: bool = Form(True)
):
    """
    Confirm and save a bank CSV import to the database.
    
    This endpoint:
    1. Validates pharmacy and bank account
    2. Parses the CSV file
    3. Creates bank_import_batch record
    4. Saves all valid transactions (with duplicate detection)
    5. Saves all errors (if any)
    
    Duplicate detection:
    - Uses external_id (unique transaction ID from bank) if available
    - Falls back to heuristic: (bank_account_id, date, amount, description)
    - Duplicates are skipped and counted in response
    
    - **pharmacy_id**: ID of the pharmacy
    - **bank_account_id**: ID of the bank account
    - **file_name**: Original filename
    - **file**: CSV file to import
    - **notes**: Optional notes about this import
    - **skip_duplicates**: Whether to skip duplicate transactions (default: true)
    """
    try:
        with get_conn() as conn, conn.cursor() as cur:
        # Validate pharmacy exists
        cur.execute(
            "SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s AND is_active = true",
            (pharmacy_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found or inactive")
        
        # Validate bank account exists and belongs to pharmacy
        cur.execute("""
            SELECT id, bank_name FROM pharma.bank_accounts
            WHERE id = %s AND pharmacy_id = %s AND is_active = true
        """, (bank_account_id, pharmacy_id))
        
        bank_account = cur.fetchone()
        if not bank_account:
            raise HTTPException(
                status_code=404,
                detail="Bank account not found, inactive, or does not belong to this pharmacy"
            )
        
        bank_name = bank_account['bank_name']
        
        # Read file content
        try:
            file_content = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Parse CSV
        try:
            valid_results, error_results = parse_csv_file(file_content, bank_name)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error parsing CSV: {str(e)}")
        
        if not valid_results:
            raise HTTPException(
                status_code=400,
                detail="No valid transactions found in file. Please check the file format."
            )
        
        # Compute period dates
        dates = [r.date for r in valid_results if r.date]
        period_start = min(dates) if dates else None
        period_end = max(dates) if dates else None
        
        # Create bank_import_batch
        cur.execute("""
            INSERT INTO pharma.bank_import_batches
            (bank_account_id, pharmacy_id, period_start, period_end, file_name, status, notes)
            VALUES (%s, %s, %s, %s, %s, 'IMPORTED', %s)
            RETURNING id
        """, (
            bank_account_id,
            pharmacy_id,
            period_start,
            period_end,
            file_name,
            notes
        ))
        
        batch_id = cur.fetchone()['id']
        
        # Insert valid transactions with batch duplicate detection
        transactions_inserted = 0
        transactions_skipped = 0
        
        if skip_duplicates and valid_results:
            # Batch duplicate detection - much faster than individual queries
            # Collect external_ids and heuristic keys
            external_ids = [r.external_id for r in valid_results if r.external_id]
            heuristic_keys = [
                (r.date, r.amount, r.description) 
                for r in valid_results 
                if not r.external_id
            ]
            
            # Check duplicates by external_id (bulk query)
            existing_external_ids = set()
            if external_ids:
                placeholders = ','.join(['%s'] * len(external_ids))
                cur.execute(f"""
                    SELECT DISTINCT external_id FROM pharma.bank_transactions
                    WHERE bank_account_id = %s AND external_id IN ({placeholders})
                """, [bank_account_id] + external_ids)
                existing_external_ids = {row['external_id'] for row in cur.fetchall()}
            
            # Check duplicates by heuristic (bulk query)
            # Use a temporary table approach for better performance with large datasets
            existing_heuristic = set()
            if heuristic_keys:
                # For large datasets, use a temp table approach
                if len(heuristic_keys) > 100:
                    # Create temp table
                    cur.execute("""
                        CREATE TEMP TABLE temp_duplicate_check (
                            check_date DATE,
                            check_amount DECIMAL,
                            check_description TEXT
                        ) ON COMMIT DROP
                    """)
                    
                    # Insert keys to check
                    cur.executemany("""
                        INSERT INTO temp_duplicate_check (check_date, check_amount, check_description)
                        VALUES (%s, %s, %s)
                    """, heuristic_keys)
                    
                    # Join with existing transactions
                    cur.execute("""
                        SELECT DISTINCT t.date, t.amount, t.description
                        FROM pharma.bank_transactions t
                        INNER JOIN temp_duplicate_check tmp
                        ON t.date = tmp.check_date
                        AND t.amount = tmp.check_amount
                        AND t.description = tmp.check_description
                        WHERE t.bank_account_id = %s
                    """, (bank_account_id,))
                    
                    existing_heuristic = {
                        (row['date'], row['amount'], row['description']) 
                        for row in cur.fetchall()
                    }
                else:
                    # For smaller datasets, use OR conditions (simpler)
                    conditions = []
                    params = [bank_account_id]
                    for date, amount, desc in heuristic_keys:
                        conditions.append("(date = %s AND amount = %s AND description = %s)")
                        params.extend([date, amount, desc])
                    
                    if conditions:
                        query = f"""
                            SELECT DISTINCT date, amount, description 
                            FROM pharma.bank_transactions
                            WHERE bank_account_id = %s AND ({' OR '.join(conditions)})
                        """
                        cur.execute(query, params)
                        existing_heuristic = {
                            (row['date'], row['amount'], row['description']) 
                            for row in cur.fetchall()
                        }
            
            # Filter out duplicates
            filtered_results = []
            for result in valid_results:
                is_duplicate = False
                
                if result.external_id:
                    if result.external_id in existing_external_ids:
                        is_duplicate = True
                else:
                    key = (result.date, result.amount, result.description)
                    if key in existing_heuristic:
                        is_duplicate = True
                
                if is_duplicate:
                    transactions_skipped += 1
                else:
                    filtered_results.append(result)
            
            valid_results = filtered_results
        
        # Batch insert transactions (much faster than individual inserts)
        # Use chunked inserts for very large datasets to avoid huge transactions
        BATCH_SIZE = 500  # Insert in batches of 500 to avoid huge transactions
        
        if valid_results:
            # Prepare batch insert data
            insert_data = []
            for result in valid_results:
                raw_description = None
                if result.raw_data:
                    raw_description = (
                        result.raw_data.get('Description') or 
                        result.raw_data.get('Transaction Description') or
                        result.raw_data.get('Narrative')
                    )
                
                # Convert Decimal to float for database insertion (PostgreSQL handles both, but float is safer)
                amount_value = float(result.amount) if result.amount is not None else None
                balance_value = float(result.balance) if result.balance is not None else None
                
                insert_data.append((
                    batch_id,
                    bank_account_id,
                    pharmacy_id,
                    result.date,
                    result.description,
                    raw_description,
                    result.reference,
                    amount_value,
                    balance_value,
                    json.dumps(result.raw_data) if result.raw_data else None,
                    result.external_id
                ))
            
            # Insert in chunks to avoid huge transactions
            for i in range(0, len(insert_data), BATCH_SIZE):
                chunk = insert_data[i:i + BATCH_SIZE]
                try:
                    cur.executemany("""
                        INSERT INTO pharma.bank_transactions
                        (bank_import_batch_id, bank_account_id, pharmacy_id, date, description,
                         raw_description, reference, amount, balance, raw_data, external_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, chunk)
                    transactions_inserted += len(chunk)
                except Exception as e:
                    # If batch insert fails, try individual inserts for this chunk
                    # This handles constraint violations gracefully
                    for data in chunk:
                        try:
                            cur.execute("""
                                INSERT INTO pharma.bank_transactions
                                (bank_import_batch_id, bank_account_id, pharmacy_id, date, description,
                                 raw_description, reference, amount, balance, raw_data, external_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, data)
                            transactions_inserted += 1
                        except Exception:
                            transactions_skipped += 1
                            continue
        
        # Insert errors
        errors_count = 0
        for idx, result in enumerate(error_results):
            try:
                row_number = result.raw_data.get('_row_number', idx + 2) if result.raw_data else idx + 2
                cur.execute("""
                    INSERT INTO pharma.bank_import_errors
                    (bank_import_batch_id, row_number, raw_data, error_message)
                    VALUES (%s, %s, %s, %s)
                """, (
                    batch_id,
                    row_number,
                    json.dumps(result.raw_data) if result.raw_data else None,
                    result.error or "Unknown error"
                ))
                errors_count += 1
            except Exception as e:
                # Log error but continue
                continue
        
            conn.commit()
            
            return ImportConfirmResponse(
                bank_import_batch_id=batch_id,
                transactions_inserted=transactions_inserted,
                transactions_skipped_as_duplicates=transactions_skipped,
                errors_count=errors_count,
                period_start=period_start.isoformat() if period_start else None,
                period_end=period_end.isoformat() if period_end else None,
                status="IMPORTED"
            )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_details = traceback.format_exc()
        logger.error(f"Error importing bank transactions: {str(e)}\n{error_details}")
        
        # Return a user-friendly error message
        raise HTTPException(
            status_code=500,
            detail=f"Error importing bank transactions: {str(e)}"
        )


@router.get("/batches/{batch_id}", response_model=BankImportBatch, dependencies=[Depends(require_api_key)])
def get_import_batch(batch_id: int):
    """Get details of a specific import batch"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, bank_account_id, pharmacy_id, period_start, period_end,
                   file_name, uploaded_by_user_id, uploaded_at, status, notes
            FROM pharma.bank_import_batches
            WHERE id = %s
        """, (batch_id,))
        
        batch = cur.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Import batch not found")
        
        return batch


@router.get("/pharmacies/{pharmacy_id}/batches", dependencies=[Depends(require_api_key)])
def list_import_batches(pharmacy_id: int, limit: int = 50, offset: int = 0):
    """List import batches for a pharmacy"""
    with get_conn() as conn, conn.cursor() as cur:
        # Verify pharmacy exists
        cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found")
        
        cur.execute("""
            SELECT id, bank_account_id, pharmacy_id, period_start, period_end,
                   file_name, uploaded_by_user_id, uploaded_at, status, notes
            FROM pharma.bank_import_batches
            WHERE pharmacy_id = %s
            ORDER BY uploaded_at DESC
            LIMIT %s OFFSET %s
        """, (pharmacy_id, limit, offset))
        
        return cur.fetchall()

