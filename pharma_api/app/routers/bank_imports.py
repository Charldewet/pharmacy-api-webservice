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
    ImportConfirmRequest, ImportConfirmResponse, BankImportBatch
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
            
            # Get period dates from summary
            period_start = import_result.summary.get('min_date')
            period_end = import_result.summary.get('max_date')
            
            return ImportConfirmResponse(
                bank_import_batch_id=import_result.bank_import_batch_id,
                transactions_inserted=import_result.transactions_inserted,
                transactions_skipped_as_duplicates=import_result.transactions_skipped_as_duplicates,
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

