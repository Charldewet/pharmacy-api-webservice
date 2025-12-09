-- ========== SEED BANK RULES ==========
-- Standard bank rules for all pharmacies
-- These rules are automatically loaded when a pharmacy is created
-- Rules are evaluated in priority order (lower number = higher priority)

-- Note: This script uses account codes and looks them up to get account_id
-- It should be run after accounts are loaded

-- Function to get account_id from account_code
CREATE OR REPLACE FUNCTION pharma.get_account_id_by_code(account_code varchar(10))
RETURNS bigint AS $$
DECLARE
    account_id bigint;
BEGIN
    SELECT id INTO account_id
    FROM pharma.accounts
    WHERE code = account_code AND is_active = true
    LIMIT 1;
    
    IF account_id IS NULL THEN
        RAISE EXCEPTION 'Account with code % not found', account_code;
    END IF;
    
    RETURN account_id;
END;
$$ LANGUAGE plpgsql;

-- Function to create standard bank rules for a pharmacy
CREATE OR REPLACE FUNCTION pharma.create_standard_bank_rules(p_pharmacy_id integer)
RETURNS void AS $$
DECLARE
    rule_id bigint;
    condition_id bigint;
BEGIN
    -- Only create if pharmacy doesn't already have rules
    IF EXISTS (SELECT 1 FROM pharma.bank_rules WHERE pharmacy_id = p_pharmacy_id) THEN
        RETURN;
    END IF;

    /* ======================= INCOMING (RECEIVE) ======================= */

    -- Rule 1: Card settlements (EFTPOS CR) → Takings Clearing
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Card settlements (EFTPOS CR) → Takings Clearing',
        'receive',
        1,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('1400'),  -- Takings Clearing
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Card Settlement',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES (rule_id, 'ALL', 'description', 'contains', 'EFTPOS SETTLEMENT CR');

    -- Rule 2: Card settlement reversals (EFTPOS DR) → Takings Clearing
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Card settlement reversals (EFTPOS DR) → Takings Clearing',
        'receive',
        2,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('1400'),  -- Takings Clearing
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Card Settlement Reversal',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES (rule_id, 'ALL', 'description', 'contains', 'EFTPOS SETTLEMENT DR');

    -- Rule 3: Cash deposits (Autosafe / ATM) → Takings Clearing
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Cash deposits (Autosafe / ATM) → Takings Clearing',
        'receive',
        3,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('1400'),  -- Takings Clearing
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Cash Deposit',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES 
        (rule_id, 'ANY', 'description', 'contains', 'CASH DEP'),
        (rule_id, 'ANY', 'description', 'contains', 'AUTOSAFE');

    -- Rule 4: Medical Aid Script Claims → Script Debtors
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Medical Aid Script Claims → Script Debtors',
        'receive',
        4,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('1100'),  -- Debtors / Trade Receivables
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Medical Aid',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES 
        (rule_id, 'ANY', 'description', 'contains', 'MEDICAL'),
        (rule_id, 'ANY', 'description', 'contains', 'SCRIPT CLAIM'),
        (rule_id, 'ANY', 'description', 'contains', 'DISCOVERY'),
        (rule_id, 'ANY', 'description', 'contains', 'MEDSCHEME');

    -- Rule 5: Interest Received → Interest Income
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Interest Received → Interest Income',
        'receive',
        5,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('4300'),  -- Interest Received
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Bank',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES (rule_id, 'ALL', 'description', 'contains', 'INTEREST');

    /* ======================= OUTGOING (SPEND) ======================= */

    -- Rule 6: Bank Charges → Bank Fees
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Bank Charges → Bank Fees',
        'spend',
        10,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('6020'),  -- Bank Charges
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Bank',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES 
        (rule_id, 'ANY', 'description', 'contains', 'BANK CHARGES'),
        (rule_id, 'ANY', 'description', 'contains', 'SERVICE FEE');

    -- Rule 7: POS Fees → POS Charges
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'POS Fees → POS Charges',
        'spend',
        11,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('6540'),  -- Merchant Fees – Bank
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Bank',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES 
        (rule_id, 'ANY', 'description', 'contains', 'POS FEE'),
        (rule_id, 'ANY', 'description', 'contains', 'MERCHANT FEE');

    -- Rule 8: Loan Repayments → Loan Accounts (Split Capital & Interest)
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Loan Repayments → Loan Accounts (Split Capital & Interest)',
        'spend',
        12,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('2200'),  -- Borrowings – Bank Loans (80% capital)
                'percent', 80,
                'vat_code', 'NO_VAT'
            ),
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('7000'),  -- Interest Paid – Loans (20% interest)
                'percent', 20,
                'vat_code', 'NO_VAT'
            )
        ),
        'Bank Loan',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES (rule_id, 'ALL', 'description', 'contains', 'LOAN');

    -- Rule 9: Supplier Payments (Wholesalers) → Cost of Sales
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Supplier Payments (Wholesalers) → Cost of Sales',
        'spend',
        13,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('5000'),  -- Cost of Sales – Merchandise
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Wholesaler',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES 
        (rule_id, 'ANY', 'description', 'contains', 'UPD'),
        (rule_id, 'ANY', 'description', 'contains', 'MEDPRO');

    -- Rule 10: Salaries & Wages → Salary Expense
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Salaries & Wages → Salary Expense',
        'spend',
        14,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('6200'),  -- Salaries & Wages
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Staff',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES 
        (rule_id, 'ANY', 'description', 'contains', 'SALARY'),
        (rule_id, 'ANY', 'description', 'contains', 'PAYROLL');

    -- Rule 11: Municipality Payments → Water & Electricity
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Municipality Payments → Water & Electricity',
        'spend',
        15,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('6110'),  -- Electricity & Water
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Municipality',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES 
        (rule_id, 'ANY', 'description', 'contains', 'MUNICIPAL'),
        (rule_id, 'ANY', 'description', 'contains', 'COUNCIL');

    -- Rule 12: Insurance Payments → Insurance Expense
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Insurance Payments → Insurance Expense',
        'spend',
        16,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('6470'),  -- Insurance – Short Term
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Insurance',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES (rule_id, 'ALL', 'description', 'contains', 'INSURANCE');

    -- Rule 13: Owner Drawings → Owners Equity
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Owner Drawings → Owners Equity',
        'spend',
        17,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('3000'),  -- Share Capital
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Owner',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES (rule_id, 'ALL', 'description', 'contains', 'OWNER');

    /* ======================= TRANSFERS ======================= */

    -- Rule 14: Transfer Between Accounts
    INSERT INTO pharma.bank_rules (pharmacy_id, name, type, priority, allocate_json, contact_name, is_active)
    VALUES (
        p_pharmacy_id,
        'Transfer Between Accounts',
        'transfer',
        30,
        jsonb_build_array(
            jsonb_build_object(
                'account_id', pharma.get_account_id_by_code('1000'),  -- Cash on Hand
                'percent', 100,
                'vat_code', 'NO_VAT'
            )
        ),
        'Internal Transfer',
        true
    )
    RETURNING id INTO rule_id;

    INSERT INTO pharma.bank_rule_conditions (bank_rule_id, group_type, field, operator, value)
    VALUES (rule_id, 'ANY', 'description', 'contains', 'TRANSFER');

END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-load rules when a pharmacy is created
CREATE OR REPLACE FUNCTION pharma.auto_create_bank_rules_for_pharmacy()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pharma.create_standard_bank_rules(NEW.pharmacy_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS trigger_auto_create_bank_rules ON pharma.pharmacies;
CREATE TRIGGER trigger_auto_create_bank_rules
    AFTER INSERT ON pharma.pharmacies
    FOR EACH ROW
    EXECUTE FUNCTION pharma.auto_create_bank_rules_for_pharmacy();

-- Load rules for existing pharmacies
DO $$
DECLARE
    pharmacy_rec RECORD;
BEGIN
    FOR pharmacy_rec IN SELECT pharmacy_id FROM pharma.pharmacies
    LOOP
        PERFORM pharma.create_standard_bank_rules(pharmacy_rec.pharmacy_id);
    END LOOP;
END $$;

