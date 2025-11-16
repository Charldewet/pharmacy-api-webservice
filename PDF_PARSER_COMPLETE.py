"""
PDF Parser for Debtor Reports
This module extracts debtor information from PDF reports.

Function: extract_debtors_strictest_names(pdf_path: str) -> pd.DataFrame

Returns a pandas DataFrame with columns:
- acc_no: Account number (string)
- name: Customer name (string)
- current: Current balance (float)
- d30: 30 days overdue (float)
- d60: 60 days overdue (float)
- d90: 90 days overdue (float)
- d120: 120 days overdue (float)
- d150: 150 days overdue (float)
- d180: 180+ days overdue (float)
- balance: Total outstanding balance (float)
- email: Email address (string, optional)
- phone: Phone number (string, optional)
"""
import pandas as pd
from typing import Optional


def extract_debtors_strictest_names(pdf_path: str) -> pd.DataFrame:
    """
    Extract debtor information from PDF report.
    
    Args:
        pdf_path: Path to the PDF file (string)
        
    Returns:
        pandas.DataFrame with debtor information
        
    Raises:
        ValueError: If PDF cannot be parsed or no debtors found
    """
    # TODO: Implement PDF parsing logic here
    # This is a placeholder - replace with actual implementation
    
    # For now, return empty DataFrame with correct structure
    # This allows the app to start, but uploads will fail until implemented
    columns = [
        'acc_no', 'name', 'current', 'd30', 'd60', 'd90', 
        'd120', 'd150', 'd180', 'balance', 'email', 'phone'
    ]
    
    # Return empty DataFrame with correct columns
    # Replace this with actual PDF parsing implementation
    df = pd.DataFrame(columns=columns)
    
    if len(df) == 0:
        raise ValueError(
            "PDF_PARSER_COMPLETE.py: extract_debtors_strictest_names() "
            "is not yet implemented. Please implement the PDF parsing logic."
        )
    
    return df

