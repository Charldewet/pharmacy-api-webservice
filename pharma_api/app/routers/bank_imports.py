"""
Bank CSV Import API Router
Handles CSV upload, parsing, preview, and import confirmation.
Based on Ruby implementation for consistency.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import date, datetime
import json
from decimal import Decimal

from ..db import get_conn
from ..schemas import (
    ImportPreviewResponse, ImportSummary, ParsedTransaction, ImportError,
    ImportConfirmRequest, ImportConfirmResponse, BankImportBatch, BankImportBatchWithDetails, SuspectedDuplicate
)
from ..auth import require_api_key
from ..services.bank_csv_parser import BankCsvParser, ParsedRow, ParseError
from ..services.bank_statement_importer import BankStatementImporter

router = APIRouter(prefix="/bank-imports", tags=["bank-imports"])


def _convert_summary_to_schema(summary: dict) -> ImportSummary:
    """Convert parser summary to ImportSummary schema"""
    return ImportSummary(
        transaction_count=summary.get('transaction_count', 0),
        total_in=summary.get('total_in', 0.0),
        total_out=summary.get('total_out', 0.0),
        min_date=summary.get('min_date'),
        max_date=summary.get('max_date')
    )


def _convert_to_parsed_transaction(row: ParsedRow) -> ParsedTransaction:
    """Convert ParsedRow to ParsedTransaction schema"""
    return ParsedTransaction(
        row_number=row.row_number,
        date=row.date.isoformat() if row.date else "",
        description=row.raw_description or row.description or "",
        reference=row.reference,
        amount=float(row.amount) if row.amount is not None else 0.0,
        balance=float(row.balance) if row.balance is not None else None
    )


def _convert_to_import_error(error: ParseError) -> ImportError:
    """Convert ParseError to ImportError schema"""
    return ImportError(
        row_number=error.row_number,
        error=error.error,
        raw_data=error.raw_data
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
    
    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    if not file_content:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Parse CSV using new parser
    try:
        parse_result = BankCsvParser.parse(file_content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing CSV: {str(e)}")
    
    # Check for suspected duplicates (without importing)
    suspected_duplicates_list = []
    try:
        with get_conn() as check_conn:
            with check_conn.cursor() as check_cur:
                # Check first 100 rows for suspected duplicates (for preview)
                preview_rows = parse_result.rows[:100]  # Check first 100 for preview
                for row in preview_rows:
                    # Check for similar matches (date + amount)
                    check_cur.execute("""
                        SELECT id, date, description, amount
                        FROM pharma.bank_transactions
                        WHERE bank_account_id = %s
                          AND date = %s
                          AND amount = %s
                        LIMIT 1
                    """, (bank_account_id, row.date, float(row.amount)))
                    match = check_cur.fetchone()
                    if match:
                        suspected_duplicates_list.append(SuspectedDuplicate(
                            row_number=row.row_number,
                            date=row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
                            description=row.description,
                            amount=float(row.amount),
                            reference=row.reference,
                            match_reason=f"Similar match: Same date ({row.date}) and amount ({row.amount})",
                            existing_transaction_id=match.get('id'),
                            existing_date=match['date'].isoformat() if hasattr(match['date'], 'isoformat') else str(match['date']),
                            existing_description=match.get('description')
                        ))
    except Exception as e:
        # If duplicate check fails, continue without suspected duplicates
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to check for suspected duplicates in preview: {str(e)}")
    
    # Convert summary
    summary = _convert_summary_to_schema(parse_result.summary)
    
    # Convert to response format
    # Sample first 20 transactions
    sample_transactions = [
        _convert_to_parsed_transaction(row)
        for row in parse_result.rows[:20]
    ]
    
    errors = [
        _convert_to_import_error(error)
        for error in parse_result.errors
    ]
    
    return ImportPreviewResponse(
        pharmacy_id=pharmacy_id,
        bank_account_id=bank_account_id,
        summary=summary,
        sample_transactions=sample_transactions,
        suspected_duplicates=suspected_duplicates_list,
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
    - Uses external_id (deterministic hash) for duplicate detection
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
        with get_conn() as conn:
            # Validate pharmacy exists
            with conn.cursor() as cur:
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
            
            # Read file content
            try:
                file_content = await file.read()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
            
            if not file_content:
                raise HTTPException(status_code=400, detail="File is empty")
            
            # Import using the new importer service
            try:
                import_result = BankStatementImporter.import_statement(
                    conn=conn,
                    pharmacy_id=pharmacy_id,
                    bank_account_id=bank_account_id,
                    file_content=file_content,
                    file_name=file_name,
                    uploaded_by_user_id=None,  # TODO: Get from auth context
                    notes=notes,
                    skip_duplicates=skip_duplicates
                )
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            except Exception as e:
                import traceback
                import logging
                logger = logging.getLogger(__name__)
                error_details = traceback.format_exc()
                logger.error(f"Error importing bank transactions: {str(e)}\n{error_details}")
                raise HTTPException(status_code=500, detail=f"Error importing bank transactions: {str(e)}")
            
            # Convert errors to schema format
            errors_list = [
                {
                    "row_number": error.row_number,
                    "error": error.error,
                    "raw_data": error.raw_data
                }
                for error in import_result.errors
            ]
            
            # Convert suspected duplicates to schema format
            suspected_duplicates_list = [
                SuspectedDuplicate(
                    row_number=dup.row_number,
                    date=dup.date.isoformat() if hasattr(dup.date, 'isoformat') else str(dup.date),
                    description=dup.description,
                    amount=float(dup.amount),
                    reference=dup.reference,
                    match_reason=dup.match_reason,
                    existing_transaction_id=dup.existing_transaction_id,
                    existing_date=dup.existing_date.isoformat() if dup.existing_date and hasattr(dup.existing_date, 'isoformat') else (str(dup.existing_date) if dup.existing_date else None),
                    existing_description=dup.existing_description
                )
                for dup in import_result.suspected_duplicates
            ]
            
            # Get period dates from summary
            period_start = import_result.summary.get('min_date')
            period_end = import_result.summary.get('max_date')
            
            return ImportConfirmResponse(
                bank_import_batch_id=import_result.bank_import_batch_id,
                transactions_inserted=import_result.transactions_inserted,
                transactions_skipped_as_duplicates=import_result.transactions_skipped_as_duplicates,
                suspected_duplicates=suspected_duplicates_list,
                errors_count=len(import_result.errors),
                period_start=period_start,
                period_end=period_end,
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


@router.get("/pharmacies/{pharmacy_id}/batches", response_model=List[BankImportBatchWithDetails], dependencies=[Depends(require_api_key)])
def list_import_batches(pharmacy_id: int, limit: int = 50, offset: int = 0):
    """
    List import batches for a pharmacy with transaction counts and bank account details.
    
    Returns batches with:
    - All batch information (id, dates, file_name, status, etc.)
    - Transaction count per batch
    - Bank account name and bank name
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Verify pharmacy exists
        cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found")
        
        # Query batches with transaction counts and bank account details
        cur.execute("""
            SELECT 
                bib.id,
                bib.bank_account_id,
                bib.pharmacy_id,
                bib.period_start,
                bib.period_end,
                bib.file_name,
                bib.uploaded_by_user_id,
                bib.uploaded_at,
                bib.status,
                bib.notes,
                COALESCE(COUNT(bt.id), 0) as transaction_count,
                ba.name as bank_account_name,
                ba.bank_name
            FROM pharma.bank_import_batches bib
            LEFT JOIN pharma.bank_transactions bt ON bt.bank_import_batch_id = bib.id
            LEFT JOIN pharma.bank_accounts ba ON bib.bank_account_id = ba.id
            WHERE bib.pharmacy_id = %s
            GROUP BY bib.id, ba.name, ba.bank_name
            ORDER BY bib.uploaded_at DESC
            LIMIT %s OFFSET %s
        """, (pharmacy_id, limit, offset))
        
        batches = cur.fetchall()
        
        # Convert to response model
        result = []
        for batch in batches:
            result.append(BankImportBatchWithDetails(
                id=batch['id'],
                bank_account_id=batch['bank_account_id'],
                pharmacy_id=batch['pharmacy_id'],
                period_start=batch['period_start'],
                period_end=batch['period_end'],
                file_name=batch['file_name'],
                uploaded_by_user_id=batch['uploaded_by_user_id'],
                uploaded_at=batch['uploaded_at'],
                status=batch['status'],
                notes=batch['notes'],
                transaction_count=batch['transaction_count'],
                bank_account_name=batch['bank_account_name'],
                bank_name=batch['bank_name']
            ))
        
        return result

