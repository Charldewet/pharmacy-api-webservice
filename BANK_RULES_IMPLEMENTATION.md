# Bank Rules & Classification System - Step 4 Complete ✅

This document describes the implementation of Step 4 of the PharmaSight Management Accounts financial system: Bank Rule Engine & Auto-Categorisation.

## Overview

The bank rules and classification system allows pharmacies to:
1. Create reusable rules to automatically categorize bank transactions
2. Use AI to suggest classifications for unmatched transactions
3. Track classification status and audit trail
4. Generate ledger entries from classified transactions

## Files Created

1. **`schema_bank_rules.sql`** - Database schema for bank rules, conditions, AI suggestions, and classification fields
2. **`pharma_api/app/services/bank_rule_engine.py`** - Core rule evaluation engine
3. **`pharma_api/app/services/bank_ai_classifier.py`** - AI classification service
4. **`pharma_api/app/routers/bank_rules.py`** - API endpoints for bank rules management
5. **Updated `pharma_api/app/schemas.py`** - Pydantic schemas for all new entities
6. **Updated `pharma_api/app/main.py`** - Registered bank_rules router

## Database Schema

### New Tables

#### `bank_rules`
Stores reusable rules per pharmacy for auto-categorizing transactions.

```sql
CREATE TABLE pharma.bank_rules (
  id                bigserial PRIMARY KEY,
  pharmacy_id       integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  name              text NOT NULL,
  type              pharma.bank_rule_type NOT NULL,  -- 'receive', 'spend', 'transfer'
  priority          integer NOT NULL DEFAULT 100,
  allocate_json     jsonb NOT NULL,  -- Array of {account_id, percent, vat_code}
  contact_name      text,
  is_active         boolean NOT NULL DEFAULT true,
  created_by_user_id bigint REFERENCES pharma.users(user_id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
```

#### `bank_rule_conditions`
Stores conditions that must match for a rule to apply.

```sql
CREATE TABLE pharma.bank_rule_conditions (
  id                bigserial PRIMARY KEY,
  bank_rule_id      bigint NOT NULL REFERENCES pharma.bank_rules(id),
  group_type        pharma.condition_group_type NOT NULL,  -- 'ALL' or 'ANY'
  field             pharma.condition_field NOT NULL,  -- 'description', 'reference', 'amount', etc.
  operator          pharma.condition_operator NOT NULL,  -- 'contains', 'equals', 'starts_with', etc.
  value             text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
```

#### `ai_suggestions`
Stores AI-generated classification suggestions.

```sql
CREATE TABLE pharma.ai_suggestions (
  id                      bigserial PRIMARY KEY,
  pharmacy_id            integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  bank_transaction_id    bigint NOT NULL REFERENCES pharma.bank_transactions(id),
  suggested_account_id  bigint NOT NULL REFERENCES pharma.accounts(id),
  suggested_description  text,
  suggested_type         pharma.bank_rule_type,
  model_name             text,
  raw_response           jsonb,
  confidence             numeric(3,2) CHECK (confidence >= 0 AND confidence <= 1),
  status                 pharma.ai_suggestion_status NOT NULL DEFAULT 'pending',
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now()
);
```

### Updated Tables

#### `bank_transactions`
Added classification fields:

```sql
ALTER TABLE pharma.bank_transactions
  ADD COLUMN classification_status pharma.classification_status NOT NULL DEFAULT 'unclassified',
  ADD COLUMN classified_at timestamptz,
  ADD COLUMN classified_by_rule_id bigint REFERENCES pharma.bank_rules(id),
  ADD COLUMN ai_suggestion_id bigint REFERENCES pharma.ai_suggestions(id),
  ADD COLUMN ledger_entry_id bigint REFERENCES pharma.ledger_entries(id);
```

#### `ledger_entries`
Added bank transaction link:

```sql
ALTER TABLE pharma.ledger_entries
  ADD COLUMN bank_transaction_id bigint REFERENCES pharma.bank_transactions(id);

CREATE UNIQUE INDEX idx_ledger_entries_bank_transaction_unique
  ON pharma.ledger_entries(bank_transaction_id)
  WHERE bank_transaction_id IS NOT NULL;
```

### New Enums

- `classification_status`: 'unclassified', 'rule_classified', 'ai_classified', 'user_override'
- `bank_rule_type`: 'receive', 'spend', 'transfer'
- `condition_group_type`: 'ALL', 'ANY'
- `condition_field`: 'description', 'reference', 'amount', 'amount_in', 'amount_out', 'date'
- `condition_operator`: 'contains', 'not_contains', 'equals', 'starts_with', 'ends_with', 'greater_than', 'less_than', 'regex'
- `ai_suggestion_status`: 'pending', 'accepted', 'rejected'

## Core Services

### BankRuleEngine

Located in `pharma_api/app/services/bank_rule_engine.py`.

**Key Methods:**
- `apply_rules_to_batch(conn, batch_id)` - Apply all rules to a batch
- `apply_rules_to_transaction(conn, transaction_id, pharmacy_id)` - Apply rules to a single transaction
- `_rule_matches(conn, rule_id, transaction)` - Check if a rule matches
- `_condition_matches(condition, transaction)` - Check if a condition matches
- `_create_ledger_entry_from_rule(conn, transaction, rule)` - Create ledger entry from matched rule

**Rule Evaluation Logic:**
1. Fetch active rules for pharmacy, ordered by priority
2. For each rule, evaluate all conditions
3. If rule matches, create ledger entry and update transaction classification
4. Uses double-entry bookkeeping (debit/credit accounts)

### BankAiClassifier

Located in `pharma_api/app/services/bank_ai_classifier.py`.

**Key Methods:**
- `suggest_for_transaction(conn, transaction_id)` - Generate AI suggestion for one transaction
- `generate_suggestions_for_batch(conn, batch_id)` - Generate suggestions for all unclassified in batch
- `_build_classification_prompt(transaction, accounts)` - Build OpenAI prompt

**AI Classification:**
- Uses OpenAI GPT-4o-mini model
- Requires `OPENAI_API_KEY` environment variable
- Returns structured JSON with suggested account code, description, type, and confidence

## API Endpoints

All endpoints are under `/bank-rules` prefix.

### Bank Rules CRUD

- `GET /bank-rules/pharmacies/{pharmacy_id}/bank-rules` - List all rules for a pharmacy
- `POST /bank-rules/pharmacies/{pharmacy_id}/bank-rules` - Create a new rule
- `GET /bank-rules/bank-rules/{rule_id}` - Get a single rule
- `PUT /bank-rules/bank-rules/{rule_id}` - Update a rule
- `DELETE /bank-rules/bank-rules/{rule_id}` - Soft delete a rule (set is_active = false)

### Rule Application

- `POST /bank-rules/bank-import-batches/{batch_id}/apply-rules` - Apply rules to all transactions in a batch
- `POST /bank-rules/bank-transactions/{transaction_id}/apply-rules` - Apply rules to a single transaction

### AI Suggestions

- `POST /bank-rules/bank-import-batches/{batch_id}/generate-ai-suggestions` - Generate AI suggestions for unclassified transactions
- `GET /bank-rules/pharmacies/{pharmacy_id}/bank-transactions/unmatched` - List all unmatched transactions
- `POST /bank-rules/ai-suggestions/{suggestion_id}/accept` - Accept an AI suggestion and create ledger entry
- `POST /bank-rules/ai-suggestions/{suggestion_id}/reject` - Reject an AI suggestion

## Usage Examples

### Creating a Bank Rule

```json
POST /bank-rules/pharmacies/1/bank-rules
{
  "name": "Card settlements → Takings Clearing",
  "type": "receive",
  "priority": 10,
  "allocate": [
    {
      "account_id": 123,
      "percent": 100,
      "vat_code": "NO_VAT"
    }
  ],
  "contact_name": "Card Settlement",
  "conditions": [
    {
      "group_type": "ALL",
      "field": "description",
      "operator": "contains",
      "value": "EFTPOS SETTLEMENT CR"
    }
  ]
}
```

### Applying Rules to a Batch

```json
POST /bank-rules/bank-import-batches/1/apply-rules

Response:
{
  "statement_id": 1,
  "total_lines": 250,
  "classified_by_rule": 180,
  "already_classified": 30,
  "unclassified": 40
}
```

### Generating AI Suggestions

```json
POST /bank-rules/bank-import-batches/1/generate-ai-suggestions

Response:
{
  "statement_id": 1,
  "unclassified_before": 40,
  "suggestions_created": 40
}
```

### Accepting an AI Suggestion

```json
POST /bank-rules/ai-suggestions/123/accept
{
  "account_id": 456  // Optional: override suggested account
}

Response:
{
  "message": "AI suggestion accepted",
  "ledger_entry_id": 789
}
```

## Setup Instructions

### 1. Apply Database Schema

Run the SQL migration:

```bash
psql -d your_database -f schema_bank_rules.sql
```

### 2. Environment Variables

For AI classification, set:

```bash
export OPENAI_API_KEY=your_openai_api_key
```

### 3. Install Dependencies

If using AI classification, install OpenAI library:

```bash
pip install openai
```

## Classification Workflow

1. **Import Bank Statement** - Transactions are imported with `classification_status = 'unclassified'`

2. **Apply Rules** - Call `POST /bank-rules/bank-import-batches/{batch_id}/apply-rules`
   - Rules are evaluated in priority order
   - Matching rules create ledger entries
   - Transactions are marked as `rule_classified`

3. **Generate AI Suggestions** - For remaining unclassified transactions, call `POST /bank-rules/bank-import-batches/{batch_id}/generate-ai-suggestions`
   - AI analyzes transaction and suggests account
   - Transactions are marked as `ai_classified`
   - Suggestions stored in `ai_suggestions` table

4. **Review & Accept** - Frontend shows unmatched transactions with AI suggestions
   - User can accept/reject suggestions
   - Accepting creates ledger entry and marks as `user_override`

5. **Manual Classification** - For transactions without rules or AI suggestions, user can manually classify (to be implemented in Step 5)

## Idempotency

- Each bank transaction can only have one ledger entry (enforced by unique index)
- Re-running rule application is safe (skips already classified transactions)
- AI suggestions can be regenerated (old suggestions are marked as rejected)

## Notes & Limitations

1. **Bank Account Mapping**: The system currently auto-detects bank ledger accounts by looking for ASSET accounts with code 1000-1999. For production, you may want to add a `ledger_account_id` field to `bank_accounts` table.

2. **Splits**: Currently supports single allocation per transaction. Multiple allocations (splits) can be added later.

3. **Double-Entry Bookkeeping**: The ledger entry creation uses simplified logic:
   - Money IN (positive): Debit Bank, Credit Income/Other
   - Money OUT (negative): Debit Expense/Other, Credit Bank

4. **AI Rate Limits**: OpenAI API has rate limits. For large batches, consider implementing queuing/background jobs.

5. **Ledger Source Enum**: The schema adds 'BANK_RULE' and 'BANK_AI' to the `ledger_source` enum, but the code currently uses 'BANK' for both. This can be updated after the enum migration.

## Next Steps (Step 5+)

- Manual classification UI
- Rule testing/preview
- Bulk rule operations
- Reconciliation reports
- Management financials generation

