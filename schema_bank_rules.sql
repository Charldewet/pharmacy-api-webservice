-- ========== BANK RULES & CLASSIFICATION SYSTEM ==========
-- Step 4: Bank Rule Engine & Auto-Categorisation

-- Classification status enum
DO $$ BEGIN
    CREATE TYPE pharma.classification_status AS ENUM (
      'unclassified',
      'rule_classified',
      'ai_classified',
      'user_override'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Bank rule type enum
DO $$ BEGIN
    CREATE TYPE pharma.bank_rule_type AS ENUM (
      'receive',
      'spend',
      'transfer'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Condition group type enum
DO $$ BEGIN
    CREATE TYPE pharma.condition_group_type AS ENUM (
      'ALL',
      'ANY'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Condition field enum
DO $$ BEGIN
    CREATE TYPE pharma.condition_field AS ENUM (
      'description',
      'reference',
      'amount',
      'amount_in',
      'amount_out',
      'date'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Condition operator enum
DO $$ BEGIN
    CREATE TYPE pharma.condition_operator AS ENUM (
      'contains',
      'not_contains',
      'equals',
      'starts_with',
      'ends_with',
      'greater_than',
      'less_than',
      'regex'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- AI suggestion status enum
DO $$ BEGIN
    CREATE TYPE pharma.ai_suggestion_status AS ENUM (
      'pending',
      'accepted',
      'rejected'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ========== BANK RULES ==========
-- Reusable rules per pharmacy for auto-categorising bank transactions
CREATE TABLE IF NOT EXISTS pharma.bank_rules (
  id                bigserial PRIMARY KEY,
  pharmacy_id       integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  name              text NOT NULL,
  type              pharma.bank_rule_type NOT NULL,
  priority          integer NOT NULL DEFAULT 100,
  allocate_json     jsonb NOT NULL,  -- Array of {account_id, percent, vat_code}
  contact_name      text,  -- Optional: for matching specific payees
  is_active         boolean NOT NULL DEFAULT true,
  created_by_user_id bigint REFERENCES pharma.users(user_id) ON DELETE SET NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bank_rules_pharmacy ON pharma.bank_rules(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_bank_rules_active ON pharma.bank_rules(pharmacy_id, is_active, priority);
CREATE INDEX IF NOT EXISTS idx_bank_rules_type ON pharma.bank_rules(type);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_bank_rule_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_bank_rule_updated_at ON pharma.bank_rules;
CREATE TRIGGER trigger_update_bank_rule_updated_at
    BEFORE UPDATE ON pharma.bank_rules
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_bank_rule_updated_at();

-- ========== BANK RULE CONDITIONS ==========
-- Conditions that must match for a rule to apply
CREATE TABLE IF NOT EXISTS pharma.bank_rule_conditions (
  id                bigserial PRIMARY KEY,
  bank_rule_id      bigint NOT NULL REFERENCES pharma.bank_rules(id) ON DELETE CASCADE,
  group_type        pharma.condition_group_type NOT NULL DEFAULT 'ALL',
  field             pharma.condition_field NOT NULL,
  operator          pharma.condition_operator NOT NULL,
  value             text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bank_rule_conditions_rule ON pharma.bank_rule_conditions(bank_rule_id);
CREATE INDEX IF NOT EXISTS idx_bank_rule_conditions_field ON pharma.bank_rule_conditions(field);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_bank_rule_condition_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_bank_rule_condition_updated_at ON pharma.bank_rule_conditions;
CREATE TRIGGER trigger_update_bank_rule_condition_updated_at
    BEFORE UPDATE ON pharma.bank_rule_conditions
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_bank_rule_condition_updated_at();

-- ========== AI SUGGESTIONS ==========
-- AI-generated classification suggestions for bank transactions
CREATE TABLE IF NOT EXISTS pharma.ai_suggestions (
  id                      bigserial PRIMARY KEY,
  pharmacy_id            integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  bank_transaction_id    bigint NOT NULL REFERENCES pharma.bank_transactions(id) ON DELETE CASCADE,
  suggested_account_id  bigint NOT NULL REFERENCES pharma.accounts(id) ON DELETE CASCADE,
  suggested_description  text,
  suggested_type         pharma.bank_rule_type,
  model_name             text,
  raw_response           jsonb,
  confidence             numeric(3,2) CHECK (confidence >= 0 AND confidence <= 1),
  status                 pharma.ai_suggestion_status NOT NULL DEFAULT 'pending',
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_suggestions_pharmacy ON pharma.ai_suggestions(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_ai_suggestions_transaction ON pharma.ai_suggestions(bank_transaction_id);
CREATE INDEX IF NOT EXISTS idx_ai_suggestions_status ON pharma.ai_suggestions(status);
CREATE INDEX IF NOT EXISTS idx_ai_suggestions_account ON pharma.ai_suggestions(suggested_account_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_ai_suggestion_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_ai_suggestion_updated_at ON pharma.ai_suggestions;
CREATE TRIGGER trigger_update_ai_suggestion_updated_at
    BEFORE UPDATE ON pharma.ai_suggestions
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_ai_suggestion_updated_at();

-- ========== UPDATE BANK TRANSACTIONS ==========
-- Add classification fields to bank_transactions
ALTER TABLE pharma.bank_transactions
  ADD COLUMN IF NOT EXISTS classification_status pharma.classification_status NOT NULL DEFAULT 'unclassified',
  ADD COLUMN IF NOT EXISTS classified_at timestamptz,
  ADD COLUMN IF NOT EXISTS classified_by_rule_id bigint REFERENCES pharma.bank_rules(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS ai_suggestion_id bigint REFERENCES pharma.ai_suggestions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS ledger_entry_id bigint REFERENCES pharma.ledger_entries(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_bank_transactions_classification ON pharma.bank_transactions(classification_status);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_rule ON pharma.bank_transactions(classified_by_rule_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_ai_suggestion ON pharma.bank_transactions(ai_suggestion_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_ledger_entry ON pharma.bank_transactions(ledger_entry_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_unclassified ON pharma.bank_transactions(pharmacy_id, classification_status) 
  WHERE classification_status IN ('unclassified', 'ai_classified');

-- ========== UPDATE LEDGER ENTRIES ==========
-- Add bank_transaction_id to ledger_entries for linking
ALTER TABLE pharma.ledger_entries
  ADD COLUMN IF NOT EXISTS bank_transaction_id bigint REFERENCES pharma.bank_transactions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ledger_entries_bank_transaction ON pharma.ledger_entries(bank_transaction_id);

-- Unique constraint: one ledger entry per bank transaction (for idempotency)
-- Note: This assumes one transaction = one ledger entry for now
-- If we need splits later, we'll need a different approach
CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_entries_bank_transaction_unique
  ON pharma.ledger_entries(bank_transaction_id)
  WHERE bank_transaction_id IS NOT NULL;

-- ========== UPDATE LEDGER SOURCE ENUM ==========
-- Add new source types to ledger_source enum
DO $$ 
BEGIN
    -- Add 'BANK_RULE' if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'BANK_RULE' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'ledger_source')
    ) THEN
        ALTER TYPE pharma.ledger_source ADD VALUE 'BANK_RULE';
    END IF;
    
    -- Add 'BANK_AI' if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'BANK_AI' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'ledger_source')
    ) THEN
        ALTER TYPE pharma.ledger_source ADD VALUE 'BANK_AI';
    END IF;
END $$;

