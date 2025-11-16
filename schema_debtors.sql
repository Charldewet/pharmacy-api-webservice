-- ========== DEBTOR REMINDER SYSTEM ==========
-- Migration to add debtor management tables

-- Extend pharmacies table with debtor-related fields
ALTER TABLE pharma.pharmacies
ADD COLUMN IF NOT EXISTS email VARCHAR(255),
ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
ADD COLUMN IF NOT EXISTS banking_account VARCHAR(50),
ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS sendgrid_api_key VARCHAR(255),  -- Encrypted
ADD COLUMN IF NOT EXISTS smsportal_client_id VARCHAR(255),  -- Encrypted
ADD COLUMN IF NOT EXISTS smsportal_api_secret VARCHAR(255);  -- Encrypted

CREATE INDEX IF NOT EXISTS idx_pharmacies_active ON pharma.pharmacies(is_active);

-- Debtor reports table
CREATE TABLE IF NOT EXISTS pharma.debtor_reports (
    id BIGSERIAL PRIMARY KEY,
    pharmacy_id INTEGER NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by BIGINT REFERENCES pharma.users(user_id) ON DELETE SET NULL,
    total_accounts INTEGER DEFAULT 0,
    total_outstanding NUMERIC(15,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_pharmacy_uploaded ON pharma.debtor_reports(pharmacy_id, uploaded_at);

-- Debtors table
CREATE TABLE IF NOT EXISTS pharma.debtors (
    id BIGSERIAL PRIMARY KEY,
    pharmacy_id INTEGER NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
    report_id BIGINT REFERENCES pharma.debtor_reports(id) ON DELETE SET NULL,
    acc_no VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    current NUMERIC(15,2) DEFAULT 0.00,
    d30 NUMERIC(15,2) DEFAULT 0.00,
    d60 NUMERIC(15,2) DEFAULT 0.00,
    d90 NUMERIC(15,2) DEFAULT 0.00,
    d120 NUMERIC(15,2) DEFAULT 0.00,
    d150 NUMERIC(15,2) DEFAULT 0.00,
    d180 NUMERIC(15,2) DEFAULT 0.00,
    balance NUMERIC(15,2) DEFAULT 0.00,
    email VARCHAR(255),
    phone VARCHAR(20),
    is_medical_aid_control BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pharmacy_id, acc_no)
);

CREATE INDEX IF NOT EXISTS idx_debtors_pharmacy_acc ON pharma.debtors(pharmacy_id, acc_no);
CREATE INDEX IF NOT EXISTS idx_debtors_balance ON pharma.debtors(pharmacy_id, balance);
CREATE INDEX IF NOT EXISTS idx_debtors_medical_aid ON pharma.debtors(pharmacy_id, is_medical_aid_control);

-- Communication logs table
CREATE TABLE IF NOT EXISTS pharma.communication_logs (
    id BIGSERIAL PRIMARY KEY,
    pharmacy_id INTEGER NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
    debtor_id BIGINT NOT NULL REFERENCES pharma.debtors(id) ON DELETE CASCADE,
    communication_type VARCHAR(10) NOT NULL CHECK (communication_type IN ('email', 'sms')),
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    external_id VARCHAR(255),
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comm_logs_pharmacy_created ON pharma.communication_logs(pharmacy_id, created_at);
CREATE INDEX IF NOT EXISTS idx_comm_logs_debtor ON pharma.communication_logs(debtor_id);
CREATE INDEX IF NOT EXISTS idx_comm_logs_status ON pharma.communication_logs(status);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_debtor_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_debtor_updated_at ON pharma.debtors;
CREATE TRIGGER trigger_update_debtor_updated_at
    BEFORE UPDATE ON pharma.debtors
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_debtor_updated_at();

