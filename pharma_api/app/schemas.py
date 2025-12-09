from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class Pharmacy(BaseModel):
    pharmacy_id: int
    name: str

class DailySales(BaseModel):
    business_date: date
    pharmacy_id: int
    turnover: Optional[float] = None
    sales_cash: Optional[float] = None
    sales_account: Optional[float] = None
    sales_cod: Optional[float] = None
    type_r_sales: Optional[float] = None
    transaction_count: Optional[int] = None
    avg_basket: Optional[float] = None
    purchases: Optional[float] = None
    cost_of_sales: Optional[float] = None
    closing_stock: Optional[float] = None
    dispensary_turnover: Optional[float] = None
    scripts_qty: Optional[int] = None
    avg_script_value: Optional[float] = None
    first_seen_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    gp_value: Optional[float] = None
    denom_excl_type_r: Optional[float] = None
    gp_pct: Optional[float] = None
    retail_excl_type_r: Optional[float] = None
    dispensary_excl_vat: Optional[float] = None
    disp_pct: Optional[float] = None
    frontshop_pct: Optional[float] = None
    frontshop_turnover: Optional[float] = None

class GPBreakdown(BaseModel):
    """GP breakdown for a single segment (dispensary or frontshop)"""
    product_count: int
    sales_value: float
    cost_of_sales: float
    gross_profit: float
    gp_percentage: float
    gp_percentage_of_total: Optional[float] = None

class FrontshopDispensaryGP(BaseModel):
    """Frontshop vs Dispensary GP breakdown using line-level data"""
    business_date: date
    pharmacy_id: int
    dispensary: GPBreakdown
    frontshop: GPBreakdown
    total: GPBreakdown
    daily_summary_gp: Optional[float] = None
    difference: Optional[float] = None

class StockItem(BaseModel):
    department_code: Optional[str] = None
    product_code: str
    description: Optional[str] = None
    qty_sold: Optional[float] = None
    sales_val: Optional[float] = None
    cost_of_sales: Optional[float] = None
    gp_value: Optional[float] = None
    gp_pct: Optional[float] = None
    on_hand: Optional[float] = None
    product_id: int

class StockPage(BaseModel):
    items: List[StockItem]
    nextCursor: Optional[str] = None

class CoverageRow(BaseModel):
    business_date: date
    pharmacy_id: int
    inv249_turnover: bool
    stk261_trading: bool
    phm080_scripts: bool
    stk260_gp: bool
    last_updated: Optional[datetime] = None

class ProductUsage(BaseModel):
    product_code: str
    description: Optional[str] = None
    avg_qty_30d: Optional[float] = None
    avg_qty_90d: Optional[float] = None
    avg_qty_180d: Optional[float] = None
    last_recalc: Optional[datetime] = None

class ProductUsagePage(BaseModel):
    items: List[ProductUsage]

class BestSellerItem(BaseModel):
    product_name: Optional[str] = None
    nappi_code: str
    quantity_sold: Optional[float] = None
    total_sales: Optional[float] = None
    gp_percent: Optional[float] = None

class BestSellerPage(BaseModel):
    items: List[BestSellerItem]

class LowGPItem(BaseModel):
    product_name: Optional[str] = None
    nappi_code: str
    quantity_sold: Optional[float] = None
    total_sales: Optional[float] = None
    total_cost: Optional[float] = None
    gp_value: Optional[float] = None
    gp_percent: Optional[float] = None

class LowGPPage(BaseModel):
    items: List[LowGPItem]

# ========== DEBTOR SCHEMAS ==========

class DebtorReport(BaseModel):
    id: int
    pharmacy_id: int
    filename: str
    file_path: Optional[str] = None
    uploaded_at: datetime
    uploaded_by: Optional[int] = None
    total_accounts: int
    total_outstanding: float
    status: str
    error_message: Optional[str] = None

class Debtor(BaseModel):
    id: int
    pharmacy_id: int
    report_id: Optional[int] = None
    acc_no: str
    name: str
    current: float
    d30: float
    d60: float
    d90: float
    d120: float
    d150: float
    d180: float
    balance: float
    email: Optional[str] = None
    phone: Optional[str] = None
    is_medical_aid_control: bool
    created_at: datetime
    updated_at: datetime

class DebtorPage(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    debtors: List[Debtor]

class DebtorStatistics(BaseModel):
    total_accounts: int
    total_outstanding: float
    current: float
    d30: float
    d60: float
    d90: float
    d120: float
    d150: float
    d180: float

class UploadDebtorReportResponse(BaseModel):
    report_id: int
    total_accounts: int
    total_outstanding: float
    debtors: List[Debtor]

class SendEmailRequest(BaseModel):
    debtor_ids: List[int]
    ageing_buckets: Optional[List[str]] = ["d60", "d90", "d120", "d150", "d180"]

class SendSMSRequest(BaseModel):
    debtor_ids: List[int]
    ageing_buckets: Optional[List[str]] = ["d60", "d90", "d120", "d150", "d180"]

class CommunicationResult(BaseModel):
    debtor_id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str
    external_id: Optional[str] = None

class CommunicationError(BaseModel):
    debtor_id: int
    error: str

class SendCommunicationResponse(BaseModel):
    sent: List[CommunicationResult]
    errors: List[CommunicationError]

class DownloadCSVRequest(BaseModel):
    debtor_ids: Optional[List[int]] = None
    min_balance: Optional[float] = None

class DownloadPDFRequest(BaseModel):
    debtor_ids: Optional[List[int]] = None
    ageing_buckets: Optional[List[str]] = None
    col_names: Optional[dict] = None

class CommunicationLog(BaseModel):
    id: int
    pharmacy_id: int
    debtor_id: int
    communication_type: str
    recipient: str
    subject: Optional[str] = None
    message: str
    status: str
    external_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

# ========== BANKING & LEDGER SCHEMAS ==========

class BankAccountBase(BaseModel):
    name: str
    bank_name: str
    account_number: Optional[str] = None
    branch_code: Optional[str] = None
    currency: str = "ZAR"
    is_active: bool = True

class BankAccountCreate(BankAccountBase):
    pharmacy_id: int

class BankAccountUpdate(BaseModel):
    name: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    branch_code: Optional[str] = None
    is_active: Optional[bool] = None

class BankAccount(BankAccountBase):
    id: int
    pharmacy_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BankImportBatch(BaseModel):
    id: int
    bank_account_id: int
    pharmacy_id: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    file_name: str
    uploaded_by_user_id: Optional[int] = None
    uploaded_at: datetime
    status: str  # IMPORTED, CLASSIFIED_PARTIAL, CLASSIFIED_COMPLETE, POSTED_TO_LEDGER
    notes: Optional[str] = None

class BankImportBatchWithDetails(BankImportBatch):
    """Enhanced BankImportBatch with transaction count and bank account details"""
    transaction_count: int = 0
    bank_account_name: Optional[str] = None
    bank_name: Optional[str] = None

class BankTransaction(BaseModel):
    id: int
    bank_import_batch_id: int
    bank_account_id: int
    pharmacy_id: int
    date: date
    description: str
    raw_description: Optional[str] = None
    reference: Optional[str] = None
    amount: float
    balance: Optional[float] = None
    raw_data: Optional[dict] = None
    external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class LedgerEntryBase(BaseModel):
    pharmacy_id: int
    date: date
    description: str
    amount: float
    debit_account_id: int
    credit_account_id: int
    source: str  # PHARMASIGHT, BANK, MANUAL
    source_reference_type: Optional[str] = None
    source_reference_id: Optional[str] = None

class LedgerEntryCreate(LedgerEntryBase):
    created_by_user_id: Optional[int] = None

class LedgerEntry(LedgerEntryBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========== BANK IMPORT SCHEMAS ==========

class ParsedTransaction(BaseModel):
    """A parsed transaction from CSV preview"""
    row_number: int
    date: str
    description: str
    reference: Optional[str] = None
    amount: float
    balance: Optional[float] = None

class ImportError(BaseModel):
    """An error encountered during CSV parsing"""
    row_number: int
    error: str
    raw_data: Optional[dict] = None

class ImportSummary(BaseModel):
    """Summary statistics for an import"""
    transaction_count: int
    total_in: float
    total_out: float
    min_date: Optional[str] = None
    max_date: Optional[str] = None

class ImportPreviewResponse(BaseModel):
    """Response from preview endpoint"""
    pharmacy_id: int
    bank_account_id: int
    summary: ImportSummary
    sample_transactions: List[ParsedTransaction]
    suspected_duplicates: List[SuspectedDuplicate] = []  # Suspected duplicates found during preview
    errors: List[ImportError]

class ImportConfirmRequest(BaseModel):
    """Request to confirm and save an import"""
    pharmacy_id: int
    bank_account_id: int
    file_name: str
    transactions: List[ParsedTransaction]
    errors: List[ImportError]
    notes: Optional[str] = None

class SuspectedDuplicate(BaseModel):
    """A transaction that might be a duplicate"""
    row_number: int
    date: str
    description: str
    amount: float
    reference: Optional[str] = None
    existing_transaction_id: Optional[int] = None
    existing_date: Optional[str] = None
    existing_description: Optional[str] = None
    match_reason: str  # e.g., "Exact match (date + amount + description)" or "Similar match (date + amount)"

class ImportConfirmResponse(BaseModel):
    """Response from confirm endpoint"""
    bank_import_batch_id: int
    transactions_inserted: int
    transactions_skipped_as_duplicates: int
    suspected_duplicates: List[SuspectedDuplicate] = []  # Transactions that might be duplicates
    errors_count: int
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    status: str

# ========== CHART OF ACCOUNTS SCHEMAS ==========

class AccountBase(BaseModel):
    code: str
    name: str
    type: str
    category: str
    parent_account_id: Optional[int] = None
    is_active: bool = True
    display_order: int = 0
    notes: Optional[str] = None

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    parent_account_id: Optional[int] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    notes: Optional[str] = None

class Account(AccountBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
