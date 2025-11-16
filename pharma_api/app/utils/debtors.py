"""
Helper functions for debtor management system
"""
import re
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from pdfminer.high_level import extract_text
from cryptography.fernet import Fernet
import base64


def is_medical_aid_control_account(name: Optional[str]) -> bool:
    """Check if account name matches medical aid control patterns."""
    if not name:
        return False
    
    name_upper = name.upper().strip()
    patterns = [
        'MEDAID CONTROL ACC',
        'MEDICAL AID CONTROL',
        'MEDICAL AID CONTROL ACCOUNT',
        'MED AID CONTROL',
        'MEDAID CONTROL',
        'MEDICAL AID ACC'
    ]
    
    return any(pattern in name_upper for pattern in patterns)


def parse_money(s: str) -> Optional[float]:
    """Parse money values like 'R 12,345.67', '(12,345.67)', '12345.67' → float."""
    if not s or not isinstance(s, str):
        return None
    
    # Remove currency symbols and spaces
    s = s.strip().upper().replace('R', '').replace('$', '').replace(',', '').strip()
    
    # Handle parentheses (negative)
    is_negative = s.startswith('(') and s.endswith(')')
    if is_negative:
        s = s[1:-1].strip()
    
    # Try to parse as float
    try:
        value = float(s)
        return -value if is_negative else value
    except (ValueError, AttributeError):
        return None


def extract_debtors_strictest_names(pdf_path: Path) -> pd.DataFrame:
    """
    Extract debtor information from PDF report.
    Returns a DataFrame with columns: acc_no, name, current, d30, d60, d90, d120, d150, d180, balance, email, phone
    """
    text = extract_text(str(pdf_path))
    if not text:
        raise ValueError("Could not extract text from PDF")
    
    lines = text.split('\n')
    debtors = []
    
    # Pattern to match account number (typically 6 digits)
    acc_no_pattern = re.compile(r'^\d{4,8}$')
    
    # Pattern to match money values
    money_pattern = re.compile(r'[R$]?\s*\(?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)?')
    
    current_debtor = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Check if line starts with account number
        parts = line.split()
        if parts and acc_no_pattern.match(parts[0]):
            # Save previous debtor if exists
            if current_debtor and current_debtor.get('acc_no'):
                debtors.append(current_debtor)
            
            # Start new debtor
            current_debtor = {
                'acc_no': parts[0],
                'name': '',
                'current': 0.0,
                'd30': 0.0,
                'd60': 0.0,
                'd90': 0.0,
                'd120': 0.0,
                'd150': 0.0,
                'd180': 0.0,
                'balance': 0.0,
                'email': '',
                'phone': ''
            }
            
            # Try to extract name (usually follows account number)
            if len(parts) > 1:
                # Name might be multiple words
                name_parts = []
                for part in parts[1:]:
                    if money_pattern.match(part):
                        break
                    name_parts.append(part)
                if name_parts:
                    current_debtor['name'] = ' '.join(name_parts)
            
            # Extract money values from the line
            money_values = money_pattern.findall(line)
            if len(money_values) >= 8:
                # Assume order: current, d30, d60, d90, d120, d150, d180, balance
                try:
                    current_debtor['current'] = parse_money(money_values[0]) or 0.0
                    current_debtor['d30'] = parse_money(money_values[1]) or 0.0
                    current_debtor['d60'] = parse_money(money_values[2]) or 0.0
                    current_debtor['d90'] = parse_money(money_values[3]) or 0.0
                    current_debtor['d120'] = parse_money(money_values[4]) or 0.0
                    current_debtor['d150'] = parse_money(money_values[5]) or 0.0
                    current_debtor['d180'] = parse_money(money_values[6]) or 0.0
                    current_debtor['balance'] = parse_money(money_values[7]) or 0.0
                except (IndexError, ValueError):
                    pass
        
        elif current_debtor:
            # Check if this line contains additional money values or contact info
            # Look for email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
            if email_match:
                current_debtor['email'] = email_match.group(0)
            
            # Look for phone (SA format: 0821234567 or +27821234567)
            phone_match = re.search(r'(\+?27|0)[0-9]{9}', line)
            if phone_match:
                current_debtor['phone'] = phone_match.group(0)
    
    # Add last debtor
    if current_debtor and current_debtor.get('acc_no'):
        debtors.append(current_debtor)
    
    if not debtors:
        raise ValueError("No debtors found in PDF")
    
    df = pd.DataFrame(debtors)
    
    # Ensure balance is calculated if missing
    if 'balance' in df.columns:
        df['balance'] = df['balance'].fillna(0)
    else:
        df['balance'] = (
            df.get('current', 0) + df.get('d30', 0) + df.get('d60', 0) +
            df.get('d90', 0) + df.get('d120', 0) + df.get('d150', 0) + df.get('d180', 0)
        )
    
    return df


def create_email_template(debtor: Dict[str, Any], pharmacy: Dict[str, Any], arrears_amount: float) -> str:
    """Create HTML email template for debtor reminder."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #d32f2f; }}
            .banking-details {{ background-color: #fff; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{pharmacy.get('name', 'Pharmacy')}</h1>
            </div>
            <div class="content">
                <p>Dear {debtor.get('name', 'Valued Customer')},</p>
                <p>We hope you're well. This is a reminder that your account at <b>{pharmacy.get('name', 'our pharmacy')}</b> 
                shows an outstanding balance of <span class="amount">R{arrears_amount:,.2f}</span>, which has been overdue 
                for more than 60 days.</p>
                <p>We kindly request that payment be made at your earliest convenience using the EFT 
                details below:</p>
                <div class="banking-details">
                    <p><b>Banking Details:</b></p>
                    <p>Bank: {pharmacy.get('bank_name', 'N/A')}<br>
                    Account Number: {pharmacy.get('banking_account', 'N/A')}<br>
                    Reference: {debtor.get('acc_no', 'N/A')}</p>
                </div>
                <p>If you've already made this payment or require a statement, please feel free to 
                contact us.</p>
                <p>Thank you for your continued support.</p>
            </div>
            <div class="footer">
                <p>Warm regards,<br>
                <b>{pharmacy.get('name', 'Pharmacy')} Team</b><br>
                {pharmacy.get('email', '')}<br>
                {pharmacy.get('phone', '')}</p>
            </div>
        </div>
    </body>
    </html>
    """


def create_sms_template(debtor: Dict[str, Any], pharmacy: Dict[str, Any], arrears_amount: float) -> str:
    """Create SMS template for debtor reminder."""
    return (
        f"Dear {debtor.get('name', 'Valued Customer')}, "
        f"Your account at {pharmacy.get('name', 'our pharmacy')} shows an outstanding balance of "
        f"R{arrears_amount:,.2f} overdue 60+ days. "
        f"Please pay via EFT: {pharmacy.get('bank_name', 'Bank')} "
        f"Acc: {pharmacy.get('banking_account', 'N/A')} Ref: {debtor.get('acc_no', 'N/A')}. "
        f"Contact: {pharmacy.get('phone', '')}"
    )


def _get_fernet():
    """Get Fernet instance using existing TOKEN_ENCRYPTION_KEY from settings."""
    from ..config import settings
    if not settings.TOKEN_ENCRYPTION_KEY:
        raise ValueError("TOKEN_ENCRYPTION_KEY not configured in settings")
    try:
        return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY: {str(e)}")


def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key before storing using existing TOKEN_ENCRYPTION_KEY."""
    if not api_key:
        return ''
    
    try:
        f = _get_fernet()
        encrypted = f.encrypt(api_key.encode("utf-8"))
        # Store as base64 string for database storage
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to encrypt API key: {str(e)}")


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key when needed using existing TOKEN_ENCRYPTION_KEY."""
    if not encrypted_key:
        return ''
    
    try:
        f = _get_fernet()
        # Decode from base64 string
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode("utf-8"))
        return f.decrypt(encrypted_bytes).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decrypt API key: {str(e)}")


def debtor_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert database row to dictionary."""
    return {
        'id': row['id'],
        'pharmacy_id': row['pharmacy_id'],
        'report_id': row.get('report_id'),
        'acc_no': str(row['acc_no']),
        'name': row['name'],
        'current': float(row['current'] or 0),
        'd30': float(row['d30'] or 0),
        'd60': float(row['d60'] or 0),
        'd90': float(row['d90'] or 0),
        'd120': float(row['d120'] or 0),
        'd150': float(row['d150'] or 0),
        'd180': float(row['d180'] or 0),
        'balance': float(row['balance'] or 0),
        'email': row.get('email') or '',
        'phone': row.get('phone') or '',
        'is_medical_aid_control': bool(row.get('is_medical_aid_control', False)),
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }

