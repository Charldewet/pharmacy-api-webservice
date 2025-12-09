"""
Bank Rules API Router
Endpoints for managing bank rules and applying them to transactions.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging
import json

from ..db import get_conn
from ..schemas import (
    BankRule, BankRuleCreate, BankRuleUpdate,
    BankRuleCondition, ApplyRulesResponse,
    GenerateAISuggestionsResponse, AcceptAISuggestionRequest,
    BankTransactionWithClassification
)
from ..services.bank_rule_engine import BankRuleEngine
from ..services.bank_ai_classifier import BankAiClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank-rules", tags=["bank-rules"])


@router.get("/pharmacies/{pharmacy_id}/bank-rules", response_model=List[BankRule])
def list_bank_rules(pharmacy_id: int):
    """List all bank rules for a pharmacy"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get rules
            cur.execute("""
                SELECT id, pharmacy_id, name, type, priority, allocate_json, contact_name,
                       is_active, created_by_user_id, created_at, updated_at
                FROM pharma.bank_rules
                WHERE pharmacy_id = %s
                ORDER BY priority ASC, created_at DESC
            """, (pharmacy_id,))
            
            rules = cur.fetchall()
            
            # Get conditions for each rule
            result = []
            for rule in rules:
                cur.execute("""
                    SELECT id, bank_rule_id, group_type, field, operator, value, created_at, updated_at
                    FROM pharma.bank_rule_conditions
                    WHERE bank_rule_id = %s
                    ORDER BY id
                """, (rule['id'],))
                
                conditions = cur.fetchall()
                
                # Convert to dict format and parse allocate_json
                rule_dict = dict(rule)
                # allocate_json is already parsed by psycopg (JSONB), so use it directly
                allocate_value = rule_dict.get('allocate_json')
                if allocate_value is None:
                    rule_dict['allocate'] = []
                elif isinstance(allocate_value, (dict, list)):
                    # Already parsed by psycopg
                    rule_dict['allocate'] = allocate_value if isinstance(allocate_value, list) else [allocate_value]
                else:
                    # String that needs parsing
                    rule_dict['allocate'] = json.loads(allocate_value)
                del rule_dict['allocate_json']  # Remove JSON field, use allocate instead
                rule_dict['conditions'] = [dict(c) for c in conditions]
                result.append(rule_dict)
            
            return result


@router.post("/pharmacies/{pharmacy_id}/bank-rules", response_model=BankRule)
def create_bank_rule(pharmacy_id: int, rule: BankRuleCreate):
    """Create a new bank rule"""
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Validate pharmacy exists
            cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Pharmacy not found")
            
            # Convert allocate to JSON
            allocate_json = json.dumps(rule.allocate)
            
            # Insert rule
            cur.execute("""
                INSERT INTO pharma.bank_rules
                (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, pharmacy_id, name, type, priority, allocate_json, contact_name,
                          is_active, created_by_user_id, created_at, updated_at
            """, (
                pharmacy_id,
                rule.name,
                rule.type,
                rule.priority,
                allocate_json,
                rule.contact_name,
                True
            ))
            
            rule_row = cur.fetchone()
            rule_id = rule_row['id']
            
            # Insert conditions
            for condition in rule.conditions:
                cur.execute("""
                    INSERT INTO pharma.bank_rule_conditions
                    (bank_rule_id, group_type, field, operator, value)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    rule_id,
                    condition.group_type,
                    condition.field,
                    condition.operator,
                    condition.value
                ))
            
            conn.commit()
            
            # Fetch full rule with conditions
            cur.execute("""
                SELECT id, pharmacy_id, name, type, priority, allocate_json, contact_name,
                       is_active, created_by_user_id, created_at, updated_at
                FROM pharma.bank_rules
                WHERE id = %s
            """, (rule_id,))
            
            rule_result = cur.fetchone()
            
            cur.execute("""
                SELECT id, bank_rule_id, group_type, field, operator, value, created_at, updated_at
                FROM pharma.bank_rule_conditions
                WHERE bank_rule_id = %s
                ORDER BY id
            """, (rule_id,))
            
            conditions = cur.fetchall()
            
            rule_dict = dict(rule_result)
            # allocate_json is already parsed by psycopg (JSONB), so use it directly
            allocate_value = rule_dict.get('allocate_json')
            if allocate_value is None:
                rule_dict['allocate'] = []
            elif isinstance(allocate_value, (dict, list)):
                # Already parsed by psycopg
                rule_dict['allocate'] = allocate_value if isinstance(allocate_value, list) else [allocate_value]
            else:
                # String that needs parsing
                rule_dict['allocate'] = json.loads(allocate_value)
            del rule_dict['allocate_json']
            rule_dict['conditions'] = [dict(c) for c in conditions]
            
            return rule_dict


@router.get("/bank-rules/{rule_id}", response_model=BankRule)
def get_bank_rule(rule_id: int):
    """Get a single bank rule"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, pharmacy_id, name, type, priority, allocate_json, contact_name,
                       is_active, created_by_user_id, created_at, updated_at
                FROM pharma.bank_rules
                WHERE id = %s
            """, (rule_id,))
            
            rule = cur.fetchone()
            if not rule:
                raise HTTPException(status_code=404, detail="Bank rule not found")
            
            cur.execute("""
                SELECT id, bank_rule_id, group_type, field, operator, value, created_at, updated_at
                FROM pharma.bank_rule_conditions
                WHERE bank_rule_id = %s
                ORDER BY id
            """, (rule_id,))
            
            conditions = cur.fetchall()
            
            rule_dict = dict(rule)
            # allocate_json is already parsed by psycopg (JSONB), so use it directly
            allocate_value = rule_dict.get('allocate_json')
            if allocate_value is None:
                rule_dict['allocate'] = []
            elif isinstance(allocate_value, (dict, list)):
                # Already parsed by psycopg
                rule_dict['allocate'] = allocate_value if isinstance(allocate_value, list) else [allocate_value]
            else:
                # String that needs parsing
                rule_dict['allocate'] = json.loads(allocate_value)
            del rule_dict['allocate_json']
            rule_dict['conditions'] = [dict(c) for c in conditions]
            
            return rule_dict


@router.put("/bank-rules/{rule_id}", response_model=BankRule)
def update_bank_rule(rule_id: int, rule_update: BankRuleUpdate):
    """Update a bank rule"""
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check rule exists
            cur.execute("SELECT id FROM pharma.bank_rules WHERE id = %s", (rule_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Bank rule not found")
            
            # Build update query
            updates = []
            params = []
            
            if rule_update.name is not None:
                updates.append("name = %s")
                params.append(rule_update.name)
            
            if rule_update.type is not None:
                updates.append("type = %s")
                params.append(rule_update.type)
            
            if rule_update.priority is not None:
                updates.append("priority = %s")
                params.append(rule_update.priority)
            
            if rule_update.allocate is not None:
                updates.append("allocate_json = %s")
                params.append(json.dumps(rule_update.allocate))
            
            if rule_update.contact_name is not None:
                updates.append("contact_name = %s")
                params.append(rule_update.contact_name)
            
            if rule_update.is_active is not None:
                updates.append("is_active = %s")
                params.append(rule_update.is_active)
            
            if updates:
                params.append(rule_id)
                cur.execute(f"""
                    UPDATE pharma.bank_rules
                    SET {', '.join(updates)}, updated_at = NOW()
                    WHERE id = %s
                """, params)
            
            # Update conditions if provided
            if rule_update.conditions is not None:
                # Delete existing conditions
                cur.execute("DELETE FROM pharma.bank_rule_conditions WHERE bank_rule_id = %s", (rule_id,))
                
                # Insert new conditions
                for condition in rule_update.conditions:
                    cur.execute("""
                        INSERT INTO pharma.bank_rule_conditions
                        (bank_rule_id, group_type, field, operator, value)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        rule_id,
                        condition.group_type,
                        condition.field,
                        condition.operator,
                        condition.value
                    ))
            
            conn.commit()
            
            # Return updated rule
            return get_bank_rule(rule_id)


@router.delete("/bank-rules/{rule_id}")
def delete_bank_rule(rule_id: int):
    """Soft delete a bank rule (set is_active = false)"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pharma.bank_rules
                SET is_active = false, updated_at = NOW()
                WHERE id = %s
            """, (rule_id,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Bank rule not found")
            
            conn.commit()
            return {"message": "Bank rule deleted"}


@router.post("/bank-import-batches/{batch_id}/apply-rules", response_model=ApplyRulesResponse)
def apply_rules_to_batch(batch_id: int):
    """Apply all active rules to transactions in a batch"""
    with get_conn() as conn:
        result = BankRuleEngine.apply_rules_to_batch(conn, batch_id)
        
        return ApplyRulesResponse(
            statement_id=batch_id,
            total_lines=result['total_lines'],
            classified_by_rule=result['classified_by_rule'],
            already_classified=result['already_classified'],
            unclassified=result['unclassified']
        )


@router.post("/bank-transactions/{transaction_id}/apply-rules")
def apply_rules_to_transaction(transaction_id: int):
    """Apply rules to a single transaction"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get pharmacy_id
            cur.execute("SELECT pharmacy_id FROM pharma.bank_transactions WHERE id = %s", (transaction_id,))
            txn = cur.fetchone()
            if not txn:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            rule_id = BankRuleEngine.apply_rules_to_transaction(conn, transaction_id, txn['pharmacy_id'])
            
            if rule_id:
                return {"message": "Rule applied", "rule_id": rule_id}
            else:
                return {"message": "No matching rule found"}


@router.post("/bank-import-batches/{batch_id}/generate-ai-suggestions", response_model=GenerateAISuggestionsResponse)
def generate_ai_suggestions_for_batch(batch_id: int):
    """Generate AI suggestions for all unclassified transactions in a batch"""
    with get_conn() as conn:
        result = BankAiClassifier.generate_suggestions_for_batch(conn, batch_id)
        
        return GenerateAISuggestionsResponse(
            statement_id=batch_id,
            unclassified_before=result['unclassified_before'],
            suggestions_created=result['suggestions_created']
        )


@router.get("/pharmacies/{pharmacy_id}/bank-transactions/unmatched", response_model=List[BankTransactionWithClassification])
def list_unmatched_transactions(pharmacy_id: int):
    """List all unmatched/unclassified transactions for a pharmacy"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT bt.id, bt.bank_import_batch_id, bt.bank_account_id, bt.pharmacy_id,
                       bt.date, bt.description, bt.raw_description, bt.reference, bt.amount,
                       bt.balance, bt.raw_data, bt.external_id, bt.created_at, bt.updated_at,
                       bt.classification_status, bt.classified_at, bt.classified_by_rule_id,
                       bt.ai_suggestion_id, bt.ledger_entry_id
                FROM pharma.bank_transactions bt
                WHERE bt.pharmacy_id = %s
                AND bt.classification_status IN ('unclassified', 'ai_classified')
                ORDER BY bt.date DESC, bt.id DESC
            """, (pharmacy_id,))
            
            transactions = cur.fetchall()
            
            # Get AI suggestions if any
            result = []
            for txn in transactions:
                txn_dict = dict(txn)
                
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
                        txn_dict['ai_suggestion'] = dict(suggestion)
                
                result.append(txn_dict)
            
            return result


@router.post("/ai-suggestions/{suggestion_id}/accept")
def accept_ai_suggestion(suggestion_id: int, request: Optional[AcceptAISuggestionRequest] = None):
    """Accept an AI suggestion and create ledger entry"""
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get suggestion
            cur.execute("""
                SELECT id, pharmacy_id, bank_transaction_id, suggested_account_id,
                       suggested_description, suggested_type
                FROM pharma.ai_suggestions
                WHERE id = %s AND status = 'pending'
            """, (suggestion_id,))
            
            suggestion = cur.fetchone()
            if not suggestion:
                raise HTTPException(status_code=404, detail="AI suggestion not found or already processed")
            
            # Get transaction
            cur.execute("""
                SELECT id, pharmacy_id, bank_account_id, date, description, amount
                FROM pharma.bank_transactions
                WHERE id = %s
            """, (suggestion['bank_transaction_id'],))
            
            txn = cur.fetchone()
            if not txn:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            # Use override account if provided, otherwise use suggested
            account_id = request.account_id if request and request.account_id else suggestion['suggested_account_id']
            
            # Find bank ledger account (same logic as rule engine)
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
                raise HTTPException(status_code=500, detail="Could not find bank ledger account")
            
            bank_ledger_account_id = bank_account_result['id']
            
            # Calculate amount
            amount = float(txn['amount'])
            allocated_amount = abs(amount)
            
            # Determine debit/credit
            if amount > 0:
                debit_account_id = bank_ledger_account_id
                credit_account_id = account_id
            else:
                debit_account_id = account_id
                credit_account_id = bank_ledger_account_id
            
            # Create ledger entry
            description = suggestion.get('suggested_description') or txn['description']
            
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
                'BANK',  # Will be 'BANK_AI' after enum update
                'bank_transaction',
                str(txn['id']),
                txn['id']
            ))
            
            ledger_entry = cur.fetchone()
            ledger_entry_id = ledger_entry['id']
            
            # Update transaction
            cur.execute("""
                UPDATE pharma.bank_transactions
                SET classification_status = 'user_override',
                    classified_at = NOW(),
                    ai_suggestion_id = %s,
                    ledger_entry_id = %s
                WHERE id = %s
            """, (suggestion_id, ledger_entry_id, txn['id']))
            
            # Update suggestion
            cur.execute("""
                UPDATE pharma.ai_suggestions
                SET status = 'accepted', updated_at = NOW()
                WHERE id = %s
            """, (suggestion_id,))
            
            conn.commit()
            
            return {
                "message": "AI suggestion accepted",
                "ledger_entry_id": ledger_entry_id
            }


@router.post("/ai-suggestions/{suggestion_id}/reject")
def reject_ai_suggestion(suggestion_id: int):
    """Reject an AI suggestion"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pharma.ai_suggestions
                SET status = 'rejected', updated_at = NOW()
                WHERE id = %s AND status = 'pending'
            """, (suggestion_id,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="AI suggestion not found or already processed")
            
            conn.commit()
            
            return {"message": "AI suggestion rejected"}

