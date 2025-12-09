"""
Bank Rule Engine
Evaluates bank rules against bank transactions and creates ledger entries.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import re

logger = logging.getLogger(__name__)


class BankRuleEngine:
    """Engine for evaluating bank rules and auto-classifying transactions"""
    
    @staticmethod
    def apply_rules_to_batch(conn, batch_id: int) -> Dict[str, int]:
        """
        Apply all active rules to all unclassified transactions in a batch.
        
        Returns:
            dict with counts: {
                'total_lines': int,
                'classified_by_rule': int,
                'already_classified': int,
                'unclassified': int
            }
        """
        with conn.cursor() as cur:
            # Get all transactions in batch
            cur.execute("""
                SELECT id, pharmacy_id, date, description, reference, amount, classification_status
                FROM pharma.bank_transactions
                WHERE bank_import_batch_id = %s
            """, (batch_id,))
            
            transactions = cur.fetchall()
            total_lines = len(transactions)
            classified_by_rule = 0
            already_classified = 0
            unclassified = 0
            
            for txn in transactions:
                # Check classification status (default to 'unclassified' if not set)
                status = txn.get('classification_status', 'unclassified')
                if status != 'unclassified':
                    already_classified += 1
                    continue
                
                result = BankRuleEngine.apply_rules_to_transaction(
                    conn, txn['id'], txn['pharmacy_id']
                )
                
                if result:
                    classified_by_rule += 1
                else:
                    unclassified += 1
            
            return {
                'total_lines': total_lines,
                'classified_by_rule': classified_by_rule,
                'already_classified': already_classified,
                'unclassified': unclassified
            }
    
    @staticmethod
    def apply_rules_to_transaction(conn, transaction_id: int, pharmacy_id: int) -> Optional[int]:
        """
        Apply rules to a single transaction.
        
        Returns:
            rule_id if a rule matched and classification was created, None otherwise
        """
        with conn.cursor() as cur:
            # Get transaction
            cur.execute("""
                SELECT id, pharmacy_id, date, description, reference, amount, classification_status
                FROM pharma.bank_transactions
                WHERE id = %s
            """, (transaction_id,))
            
            txn = cur.fetchone()
            if not txn:
                return None
            
            # Skip if already classified (default to 'unclassified' if not set)
            status = txn.get('classification_status', 'unclassified')
            if status != 'unclassified':
                return None
            
            # Get active rules for this pharmacy, ordered by priority
            cur.execute("""
                SELECT id, name, type, priority, allocate_json, contact_name
                FROM pharma.bank_rules
                WHERE pharmacy_id = %s AND is_active = true
                ORDER BY priority ASC
            """, (pharmacy_id,))
            
            rules = cur.fetchall()
            
            # Try each rule
            for rule in rules:
                if BankRuleEngine._rule_matches(conn, rule['id'], txn):
                    # Rule matched - create ledger entry
                    ledger_entry_id = BankRuleEngine._create_ledger_entry_from_rule(
                        conn, txn, rule
                    )
                    
                    # Update transaction classification
                    cur.execute("""
                        UPDATE pharma.bank_transactions
                        SET classification_status = 'rule_classified',
                            classified_at = NOW(),
                            classified_by_rule_id = %s,
                            ledger_entry_id = %s
                        WHERE id = %s
                    """, (rule['id'], ledger_entry_id, transaction_id))
                    
                    conn.commit()
                    logger.info(f"Rule {rule['id']} matched transaction {transaction_id}")
                    return rule['id']
            
            return None
    
    @staticmethod
    def _rule_matches(conn, rule_id: int, transaction: Dict[str, Any]) -> bool:
        """
        Check if a rule matches a transaction by evaluating all conditions.
        
        Returns:
            True if rule matches, False otherwise
        """
        with conn.cursor() as cur:
            # Get all conditions for this rule
            cur.execute("""
                SELECT group_type, field, operator, value
                FROM pharma.bank_rule_conditions
                WHERE bank_rule_id = %s
                ORDER BY id
            """, (rule_id,))
            
            conditions = cur.fetchall()
            
            if not conditions:
                return False  # Rule with no conditions doesn't match
            
            # Group conditions by group_type
            all_conditions = [c for c in conditions if c['group_type'] == 'ALL']
            any_conditions = [c for c in conditions if c['group_type'] == 'ANY']
            
            # ALL conditions must all match
            if all_conditions:
                for condition in all_conditions:
                    if not BankRuleEngine._condition_matches(condition, transaction):
                        return False
            
            # ANY conditions - at least one must match
            if any_conditions:
                any_matched = False
                for condition in any_conditions:
                    if BankRuleEngine._condition_matches(condition, transaction):
                        any_matched = True
                        break
                if not any_matched:
                    return False
            
            return True
    
    @staticmethod
    def _condition_matches(condition: Dict[str, Any], transaction: Dict[str, Any]) -> bool:
        """
        Check if a single condition matches a transaction.
        
        Returns:
            True if condition matches, False otherwise
        """
        field = condition['field']
        operator = condition['operator']
        value = condition['value']
        
        # Get field value from transaction
        if field == 'description':
            field_value = transaction.get('description', '') or ''
        elif field == 'reference':
            field_value = transaction.get('reference', '') or ''
        elif field == 'amount':
            field_value = float(transaction.get('amount', 0))
        elif field == 'amount_in':
            # amount_in is positive amount
            amount = float(transaction.get('amount', 0))
            field_value = amount if amount > 0 else 0
        elif field == 'amount_out':
            # amount_out is absolute value of negative amount
            amount = float(transaction.get('amount', 0))
            field_value = abs(amount) if amount < 0 else 0
        elif field == 'date':
            field_value = transaction.get('date')
        else:
            return False
        
        # Apply operator
        if operator == 'contains':
            return str(value).lower() in str(field_value).lower()
        elif operator == 'not_contains':
            return str(value).lower() not in str(field_value).lower()
        elif operator == 'equals':
            return str(field_value).lower() == str(value).lower()
        elif operator == 'starts_with':
            return str(field_value).lower().startswith(str(value).lower())
        elif operator == 'ends_with':
            return str(field_value).lower().endswith(str(value).lower())
        elif operator == 'greater_than':
            try:
                return float(field_value) > float(value)
            except (ValueError, TypeError):
                return False
        elif operator == 'less_than':
            try:
                return float(field_value) < float(value)
            except (ValueError, TypeError):
                return False
        elif operator == 'regex':
            try:
                return bool(re.search(value, str(field_value), re.IGNORECASE))
            except re.error:
                return False
        
        return False
    
    @staticmethod
    def _create_ledger_entry_from_rule(conn, transaction: Dict[str, Any], rule: Dict[str, Any]) -> int:
        """
        Create ledger entry(s) from a matched rule.
        
        For now, we support single allocation (one ledger entry per transaction).
        Splits (multiple allocations) can be added later.
        
        Returns:
            ledger_entry_id
        """
        import json
        
        with conn.cursor() as cur:
            # Parse allocate_json
            allocate = rule['allocate_json']
            if isinstance(allocate, str):
                allocate = json.loads(allocate)
            
            if not allocate or len(allocate) == 0:
                raise ValueError(f"Rule {rule['id']} has no allocations")
            
            # For now, use first allocation (single entry)
            # TODO: Support splits (multiple ledger entries)
            allocation = allocate[0]
            account_id = allocation['account_id']
            percent = allocation.get('percent', 100)
            
            # Calculate amount
            amount = float(transaction['amount'])
            allocated_amount = abs(amount) * (percent / 100.0)
            
            # Get the bank account for this transaction
            cur.execute("""
                SELECT bank_account_id FROM pharma.bank_transactions WHERE id = %s
            """, (transaction['id'],))
            txn_detail = cur.fetchone()
            bank_account_id = txn_detail['bank_account_id'] if txn_detail else None
            
            # Find the ledger account for this bank account
            # We'll look for a bank account in the accounts table by matching name or using a default
            # For now, we'll try to find an account with code starting with '1' (Assets) and type 'ASSET'
            # that might be a bank account, or use a default
            bank_ledger_account_id = None
            
            if bank_account_id:
                # Try to find bank account by matching bank account name
                cur.execute("""
                    SELECT ba.name, ba.bank_name
                    FROM pharma.bank_accounts ba
                    WHERE ba.id = %s
                """, (bank_account_id,))
                bank_account = cur.fetchone()
                
                if bank_account:
                    # Try to find matching account in chart of accounts
                    # Look for accounts with "Bank" or "Cash" in name, type ASSET
                    cur.execute("""
                        SELECT id FROM pharma.accounts
                        WHERE type = 'ASSET'
                        AND (LOWER(name) LIKE '%bank%' OR LOWER(name) LIKE '%cash%')
                        AND is_active = true
                        ORDER BY code
                        LIMIT 1
                    """)
                    bank_account_result = cur.fetchone()
                    if bank_account_result:
                        bank_ledger_account_id = bank_account_result['id']
            
            # If we still don't have a bank ledger account, use a default
            # Look for account code 1000-1999 (Assets) that might be bank
            if not bank_ledger_account_id:
                cur.execute("""
                    SELECT id FROM pharma.accounts
                    WHERE code >= '1000' AND code < '2000'
                    AND type = 'ASSET'
                    AND is_active = true
                    ORDER BY code
                    LIMIT 1
                """)
                bank_account_result = cur.fetchone()
                if bank_account_result:
                    bank_ledger_account_id = bank_account_result['id']
            
            if not bank_ledger_account_id:
                raise ValueError(f"Could not find a bank ledger account for transaction {transaction['id']}. Please configure bank account mapping.")
            
            # Build description
            description = transaction.get('description', '')
            if rule.get('contact_name'):
                description = f"{description} ({rule['contact_name']})"
            
            # Determine debit/credit based on transaction amount
            # Double-entry bookkeeping:
            # - Positive amount (money in): Debit Bank, Credit Income/Other
            # - Negative amount (money out): Debit Expense/Other, Credit Bank
            if amount > 0:
                # Money coming in
                debit_account_id = bank_ledger_account_id
                credit_account_id = account_id
            else:
                # Money going out
                debit_account_id = account_id
                credit_account_id = bank_ledger_account_id
            
            # Insert ledger entry
            # Use 'BANK' source for now (will be 'BANK_RULE' after enum update)
            cur.execute("""
                INSERT INTO pharma.ledger_entries
                (pharmacy_id, date, description, amount, debit_account_id, credit_account_id,
                 source, source_reference_type, source_reference_id, bank_transaction_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                transaction['pharmacy_id'],
                transaction['date'],
                description,
                allocated_amount,
                debit_account_id,
                credit_account_id,
                'BANK',  # Will be updated to 'BANK_RULE' after enum update
                'bank_transaction',
                str(transaction['id']),
                transaction['id']
            ))
            
            result = cur.fetchone()
            return result['id']

