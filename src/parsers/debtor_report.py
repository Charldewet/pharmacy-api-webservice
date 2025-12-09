"""
Parser for Debtor Reports (DEB013)

Extracts debtor account information from PDF reports.
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path to import PDF_PARSER_COMPLETE
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PDF_PARSER_COMPLETE import extract_debtors_strictest_names


def parse_debtor_report(pdf_path: Path) -> Dict[str, Any]:
    """
    Parse a debtor report PDF and return structured data.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary with:
        - pharmacy_id: Pharmacy ID (must be set by caller)
        - report_type: "debtor_report"
        - debtors: List of debtor records
        - total_accounts: Total number of accounts
        - total_outstanding: Total outstanding balance
    """
    # Extract debtors from PDF
    df = extract_debtors_strictest_names(str(pdf_path))
    
    # Convert DataFrame to list of dictionaries
    debtors = df.to_dict('records')
    
    # Calculate totals
    total_accounts = len(debtors)
    total_outstanding = float(df['balance'].sum()) if not df.empty else 0.0
    
    return {
        "report_type": "debtor_report",
        "debtors": debtors,
        "total_accounts": total_accounts,
        "total_outstanding": total_outstanding,
    }



