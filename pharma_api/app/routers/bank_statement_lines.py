"""
Bank Statement Lines API Router
Endpoints for manual classification of bank transactions.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from decimal import Decimal
import logging

from ..db import get_conn
from ..schemas import ManualClassifyRequest, ManualClassifyResponse, BankTransactionWithClassification
from ..auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank-statement-lines", tags=["bank-statement-lines"])


@router.post("/{line_id}/manual-classify", response_model=ManualClassifyResponse, dependencies=[Depends(require_api_key)])
def manual_classify_transaction(line_id: int, request: ManualClassifyRequest):
    """
    Manually classify a bank statement line (transaction).
    
    This creates a ledger entry and marks the transaction as user_override.
    Only one ledger entry can be created per bank transaction (enforced by unique constraint).
    
    - **line_id**: ID of the bank_transaction (bank statement line)
    - **account_id**: Account ID to classify this transaction to
    - **description**: Optional description override (uses transaction description if not provided)
    - **note**: Optional note for audit trail (stored in ledger entry if needed)
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Get the bank transaction
                cur.execute("""
                    SELECT id, pharmacy_id, bank_account_id, date, description, amount,
                           classification_status, ledger_entry_id
                    FROM pharma.bank_transactions
                    WHERE id = %s
                """, (line_id,))
                
                txn = cur.fetchone()
                if not txn:
                    raise HTTPException(status_code=404, detail=f"Bank statement line {line_id} not found")
                
                # Check if already classified (has ledger entry)
                if txn['ledger_entry_id']:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Transaction {line_id} already has a ledger entry (id: {txn['ledger_entry_id']}). Cannot create duplicate."
                    )
                
                # Validate account exists and is active
                # Note: accounts table is global (shared across all pharmacies), no pharmacy_id column
                cur.execute("""
                    SELECT id, is_active
                    FROM pharma.accounts
                    WHERE id = %s AND is_active = true
                """, (request.account_id,))
                
                account = cur.fetchone()
                if not account:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Account {request.account_id} not found or is inactive"
                    )
                
                # Compute signed amount
                # The amount field already has the sign: positive = income, negative = expense
                amount = float(txn['amount'])
                allocated_amount = abs(amount)
                
                # Find the bank ledger account (same logic as rule engine)
                cur.execute("""
                    SELECT id FROM pharma.accounts
                    WHERE code >= '1000' AND code < '2000'
                    AND type = 'ASSET'
                    AND is_active = true
                    ORDER BY code
                    LIMIT 1
                """)
                bank_account_result = cur.fetchone()
                if not bank_account_result:
                    raise HTTPException(
                        status_code=500,
                        detail="Could not find bank ledger account. Please configure a bank account in the chart of accounts."
                    )
                
                bank_ledger_account_id = bank_account_result['id']
                
                # Determine debit/credit based on transaction amount
                # Double-entry bookkeeping:
                # - Positive amount (money in): Debit Bank, Credit Income/Other
                # - Negative amount (money out): Debit Expense/Other, Credit Bank
                if amount > 0:
                    debit_account_id = bank_ledger_account_id
                    credit_account_id = request.account_id
                else:
                    debit_account_id = request.account_id
                    credit_account_id = bank_ledger_account_id
                
                # Use user-provided description or default to transaction description
                description = request.description or txn['description']
                
                # Create ledger entry
                # The unique constraint on bank_transaction_id will prevent duplicates
                try:
                    cur.execute("""
                        INSERT INTO pharma.ledger_entries
                        (pharmacy_id, date, description, amount, debit_account_id, credit_account_id,
                         source, source_reference_type, source_reference_id, bank_transaction_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        txn['pharmacy_id'],
                        txn['date'],
                        description,
                        allocated_amount,
                        debit_account_id,
                        credit_account_id,
                        'MANUAL',  # Source is MANUAL for user override
                        'bank_transaction',
                        str(txn['id']),
                        txn['id']
                    ))
                    
                    ledger_entry = cur.fetchone()
                    if not ledger_entry:
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to create ledger entry: No ID returned from INSERT"
                        )
                    ledger_entry_id = ledger_entry['id']
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    logger.error(f"Error creating ledger entry for transaction {line_id}: {str(e)}\n{error_trace}")
                    
                    # Check if it's a unique constraint violation
                    error_msg = str(e).lower()
                    if 'unique' in error_msg or 'duplicate' in error_msg or 'already exists' in error_msg:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Transaction {line_id} already has a ledger entry. Cannot create duplicate."
                        )
                    
                    # Check if it's a column doesn't exist error
                    if 'column' in error_msg and 'does not exist' in error_msg:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Database schema error: {str(e)}. Please ensure bank_rules schema migration has been applied."
                        )
                    
                    # Check if it's an enum value error
                    if 'invalid input value for enum' in error_msg or 'invalid value for enum' in error_msg:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Invalid enum value: {str(e)}. Please ensure MANUAL is a valid ledger_source value."
                        )
                    
                    # Generic error with full details for debugging
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create ledger entry: {str(e)}"
                    )
                
                # Update bank transaction
                cur.execute("""
                    UPDATE pharma.bank_transactions
                    SET classification_status = 'user_override',
                        classified_at = NOW(),
                        ledger_entry_id = %s
                    WHERE id = %s
                """, (ledger_entry_id, line_id))
                
                conn.commit()
                
                logger.info(f"Manually classified transaction {line_id} to account {request.account_id}, created ledger entry {ledger_entry_id}")
                
                return ManualClassifyResponse(
                    message="Transaction manually classified",
                    ledger_entry_id=ledger_entry_id,
                    bank_transaction_id=line_id,
                    classification_status='user_override'
                )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Unexpected error in manual_classify_transaction for line {line_id}: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/{line_id}", response_model=BankTransactionWithClassification, dependencies=[Depends(require_api_key)])
def get_bank_statement_line(line_id: int):
    """
    Get a single bank statement line (transaction) with classification details.
    
    - **line_id**: ID of the bank_transaction
    """
    from ..schemas import AISuggestion
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, bank_import_batch_id, bank_account_id, pharmacy_id,
                       date, description, raw_description, reference, amount,
                       balance, raw_data, external_id, created_at, updated_at,
                       classification_status, classified_at, classified_by_rule_id,
                       ai_suggestion_id, ledger_entry_id
                FROM pharma.bank_transactions
                WHERE id = %s
            """, (line_id,))
            
            txn = cur.fetchone()
            if not txn:
                raise HTTPException(status_code=404, detail=f"Bank statement line {line_id} not found")
            
            txn_dict = dict(txn)
            
            # Convert Decimal to float for JSON serialization
            if isinstance(txn_dict.get('amount'), Decimal):
                txn_dict['amount'] = float(txn_dict['amount'])
            if isinstance(txn_dict.get('balance'), Decimal):
                txn_dict['balance'] = float(txn_dict['balance']) if txn_dict['balance'] else None
            
            # Convert date to string (Pydantic will parse it)
            if txn_dict.get('date'):
                txn_dict['date'] = str(txn_dict['date'])
            
            # Convert datetime to ISO string
            if txn_dict.get('created_at'):
                txn_dict['created_at'] = txn_dict['created_at'].isoformat()
            if txn_dict.get('updated_at'):
                txn_dict['updated_at'] = txn_dict['updated_at'].isoformat()
            if txn_dict.get('classified_at'):
                txn_dict['classified_at'] = txn_dict['classified_at'].isoformat()
            
            # Get AI suggestion if any
            if txn['ai_suggestion_id']:
                cur.execute("""
                    SELECT id, pharmacy_id, bank_transaction_id, suggested_account_id,
                           suggested_description, suggested_type, model_name, raw_response,
                           confidence, status, created_at, updated_at
                    FROM pharma.ai_suggestions
                    WHERE id = %s
                """, (txn['ai_suggestion_id'],))
                
                suggestion = cur.fetchone()
                if suggestion:
                    suggestion_dict = dict(suggestion)
                    # Convert Decimal confidence to float
                    if isinstance(suggestion_dict.get('confidence'), Decimal):
                        suggestion_dict['confidence'] = float(suggestion_dict['confidence'])
                    # Convert datetime to ISO string
                    if suggestion_dict.get('created_at'):
                        suggestion_dict['created_at'] = suggestion_dict['created_at'].isoformat()
                    if suggestion_dict.get('updated_at'):
                        suggestion_dict['updated_at'] = suggestion_dict['updated_at'].isoformat()
                    txn_dict['ai_suggestion'] = suggestion_dict
            
            return BankTransactionWithClassification(**txn_dict)
