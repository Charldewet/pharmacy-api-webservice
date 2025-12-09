"""
Bank AI Classifier
Uses AI to suggest account classifications for unclassified bank transactions.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BankAiClassifier:
    """AI service for classifying bank transactions"""
    
    @staticmethod
    def suggest_for_transaction(conn, transaction_id: int) -> Optional[int]:
        """
        Generate an AI suggestion for a single transaction.
        
        Returns:
            ai_suggestion_id if suggestion was created, None otherwise
        """
        try:
            import openai
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            return None
        
        with conn.cursor() as cur:
            # Get transaction
            cur.execute("""
                SELECT id, pharmacy_id, date, description, reference, amount
                FROM pharma.bank_transactions
                WHERE id = %s
            """, (transaction_id,))
            
            txn = cur.fetchone()
            if not txn:
                return None
            
            # Skip if already classified
            if txn.get('classification_status') != 'unclassified':
                return None
            
            # Get available accounts for this pharmacy
            cur.execute("""
                SELECT id, code, name, type, category
                FROM pharma.accounts
                WHERE is_active = true
                ORDER BY code
            """)
            
            accounts = cur.fetchall()
            
            # Build prompt
            prompt = BankAiClassifier._build_classification_prompt(txn, accounts)
            
            # Call OpenAI
            try:
                # Get API key from environment
                import os
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    logger.warning("OPENAI_API_KEY not set. Skipping AI classification.")
                    return None
                
                client = openai.OpenAI(api_key=api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # Use cheaper model for classification
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an accounting assistant that classifies bank transactions into appropriate chart of accounts categories. Return your response as valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                
                result = json.loads(response.choices[0].message.content)
                
                # Extract suggestion
                suggested_account_code = result.get('suggested_account_code')
                suggested_description = result.get('suggested_description')
                suggested_type = result.get('type', 'spend')  # 'receive', 'spend', 'transfer'
                confidence = result.get('confidence', 0.5)
                
                # Find account by code
                suggested_account_id = None
                for account in accounts:
                    if account['code'] == suggested_account_code:
                        suggested_account_id = account['id']
                        break
                
                if not suggested_account_id:
                    logger.warning(f"Could not find account with code {suggested_account_code}")
                    return None
                
                # Save suggestion
                cur.execute("""
                    INSERT INTO pharma.ai_suggestions
                    (pharmacy_id, bank_transaction_id, suggested_account_id, suggested_description,
                     suggested_type, model_name, raw_response, confidence, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    txn['pharmacy_id'],
                    transaction_id,
                    suggested_account_id,
                    suggested_description,
                    suggested_type,
                    'gpt-4o-mini',
                    json.dumps(result),
                    confidence,
                    'pending'
                ))
                
                suggestion = cur.fetchone()
                suggestion_id = suggestion['id']
                
                # Update transaction
                cur.execute("""
                    UPDATE pharma.bank_transactions
                    SET classification_status = 'ai_classified',
                        ai_suggestion_id = %s
                    WHERE id = %s
                """, (suggestion_id, transaction_id))
                
                conn.commit()
                logger.info(f"Created AI suggestion {suggestion_id} for transaction {transaction_id}")
                return suggestion_id
                
            except Exception as e:
                logger.error(f"Error calling OpenAI API: {str(e)}")
                conn.rollback()
                return None
    
    @staticmethod
    def _build_classification_prompt(transaction: Dict[str, Any], accounts: List[Dict[str, Any]]) -> str:
        """Build the prompt for AI classification"""
        
        # Format accounts list
        accounts_list = []
        for acc in accounts:
            accounts_list.append(f"- Code: {acc['code']}, Name: {acc['name']}, Type: {acc['type']}, Category: {acc['category']}")
        
        accounts_text = "\n".join(accounts_list)
        
        # Determine amount direction
        amount = float(transaction.get('amount', 0))
        amount_str = f"R {abs(amount):,.2f}"
        if amount > 0:
            direction = "Money IN (credit)"
        else:
            direction = "Money OUT (debit)"
        
        prompt = f"""Classify the following bank transaction into the most appropriate chart of accounts account.

Transaction Details:
- Date: {transaction.get('date')}
- Description: {transaction.get('description', '')}
- Reference: {transaction.get('reference', 'N/A')}
- Amount: {amount_str} ({direction})

Available Accounts:
{accounts_text}

Return a JSON object with the following structure:
{{
  "suggested_account_code": "string (the account code from the list above)",
  "suggested_description": "string (cleaned/standardized description for the ledger)",
  "type": "receive|spend|transfer",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of why this account was chosen"
}}

Choose the most appropriate account based on:
1. The transaction description and reference
2. The account type and category
3. Whether money is coming in or going out

For money IN (positive amounts), typically use INCOME, OTHER_INCOME, or ASSET accounts.
For money OUT (negative amounts), typically use EXPENSE, COGS, or ASSET accounts."""
        
        return prompt
    
    @staticmethod
    def generate_suggestions_for_batch(conn, batch_id: int) -> Dict[str, int]:
        """
        Generate AI suggestions for all unclassified transactions in a batch.
        
        Returns:
            dict with counts: {
                'unclassified_before': int,
                'suggestions_created': int
            }
        """
        with conn.cursor() as cur:
            # Get unclassified transactions
            cur.execute("""
                SELECT id FROM pharma.bank_transactions
                WHERE bank_import_batch_id = %s
                AND classification_status = 'unclassified'
            """, (batch_id,))
            
            transactions = cur.fetchall()
            unclassified_before = len(transactions)
            suggestions_created = 0
            
            for txn in transactions:
                suggestion_id = BankAiClassifier.suggest_for_transaction(conn, txn['id'])
                if suggestion_id:
                    suggestions_created += 1
            
            return {
                'unclassified_before': unclassified_before,
                'suggestions_created': suggestions_created
            }

