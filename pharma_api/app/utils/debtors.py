"""
Helper functions for debtor management system
"""
from typing import Optional, Dict, Any
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


# extract_debtors_strictest_names is now imported from PDF_PARSER_COMPLETE module

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

