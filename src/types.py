from enum import Enum

class ReportType(str, Enum):
    GP_REPORT = "gross_profit"             # STK260: per-SKU/department
    TRADING_ACCOUNT = "trading_account"    # STK261: opening/purchases/COS/closing
    TURNOVER_SUMMARY = "turnover_summary"  # INV249: turnover + counts/averages
    DISPENSARY_SCRIPTS = "dispensary_scripts"  # PHM080: Script Statistics

class PharmacyId(int, Enum):
    REITZ = 1
    WINTERTON = 2
    ROOS = 3
    VILLIERS = 4
    TUGELA = 5
    UMDONI = 101
