#!/usr/bin/env python3
"""
Helper script to configure pharmacy settings for debtor management system.
Usage: python scripts/configure_pharmacy_debtors.py <pharmacy_id>
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv('pharma_api/.env')

from pharma_api.app.db import get_conn
from pharma_api.app.utils.debtors import encrypt_api_key

def configure_pharmacy(pharmacy_id: int, email: str = None, phone: str = None,
                      banking_account: str = None, bank_name: str = None,
                      sendgrid_api_key: str = None, smsportal_client_id: str = None,
                      smsportal_api_secret: str = None):
    """Configure pharmacy settings for debtor management"""
    
    with get_conn() as conn, conn.cursor() as cur:
        # Check if pharmacy exists
        cur.execute("SELECT pharmacy_id, name FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
        pharmacy = cur.fetchone()
        
        if not pharmacy:
            print(f"✗ Pharmacy ID {pharmacy_id} not found")
            return False
        
        print(f"Configuring pharmacy: {pharmacy['name']} (ID: {pharmacy_id})")
        
        # Build update query
        updates = []
        params = []
        
        if email:
            updates.append("email = %s")
            params.append(email)
        
        if phone:
            updates.append("phone = %s")
            params.append(phone)
        
        if banking_account:
            updates.append("banking_account = %s")
            params.append(banking_account)
        
        if bank_name:
            updates.append("bank_name = %s")
            params.append(bank_name)
        
        if sendgrid_api_key:
            encrypted_key = encrypt_api_key(sendgrid_api_key)
            updates.append("sendgrid_api_key = %s")
            params.append(encrypted_key)
            print("  ✓ Encrypted and stored SendGrid API key (using existing TOKEN_ENCRYPTION_KEY)")
        
        if smsportal_client_id:
            encrypted_id = encrypt_api_key(smsportal_client_id)
            updates.append("smsportal_client_id = %s")
            params.append(encrypted_id)
            print("  ✓ Encrypted and stored SMS Portal client ID (using existing TOKEN_ENCRYPTION_KEY)")
        
        if smsportal_api_secret:
            encrypted_secret = encrypt_api_key(smsportal_api_secret)
            updates.append("smsportal_api_secret = %s")
            params.append(encrypted_secret)
            print("  ✓ Encrypted and stored SMS Portal API secret (using existing TOKEN_ENCRYPTION_KEY)")
        
        if not updates:
            print("  ✗ No updates provided")
            return False
        
        params.append(pharmacy_id)
        
        query = f"UPDATE pharma.pharmacies SET {', '.join(updates)} WHERE pharmacy_id = %s"
        cur.execute(query, params)
        conn.commit()
        
        print(f"✓ Pharmacy {pharmacy_id} configured successfully!")
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/configure_pharmacy_debtors.py <pharmacy_id> [options]")
        print("\nOptions:")
        print("  --email <email>")
        print("  --phone <phone>")
        print("  --banking-account <account>")
        print("  --bank-name <name>")
        print("  --sendgrid-api-key <key>")
        print("  --smsportal-client-id <id>")
        print("  --smsportal-api-secret <secret>")
        print("\nExample:")
        print("  python scripts/configure_pharmacy_debtors.py 1 \\")
        print("    --email pharmacy@example.com \\")
        print("    --phone 0821234567 \\")
        print("    --banking-account 1234567890 \\")
        print("    --bank-name ABSA \\")
        print("    --sendgrid-api-key SG.xxxxx")
        sys.exit(1)
    
    pharmacy_id = int(sys.argv[1])
    
    # Parse arguments
    email = None
    phone = None
    banking_account = None
    bank_name = None
    sendgrid_api_key = None
    smsportal_client_id = None
    smsportal_api_secret = None
    
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--email' and i + 1 < len(sys.argv):
            email = sys.argv[i + 1]
            i += 2
        elif arg == '--phone' and i + 1 < len(sys.argv):
            phone = sys.argv[i + 1]
            i += 2
        elif arg == '--banking-account' and i + 1 < len(sys.argv):
            banking_account = sys.argv[i + 1]
            i += 2
        elif arg == '--bank-name' and i + 1 < len(sys.argv):
            bank_name = sys.argv[i + 1]
            i += 2
        elif arg == '--sendgrid-api-key' and i + 1 < len(sys.argv):
            sendgrid_api_key = sys.argv[i + 1]
            i += 2
        elif arg == '--smsportal-client-id' and i + 1 < len(sys.argv):
            smsportal_client_id = sys.argv[i + 1]
            i += 2
        elif arg == '--smsportal-api-secret' and i + 1 < len(sys.argv):
            smsportal_api_secret = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    configure_pharmacy(
        pharmacy_id=pharmacy_id,
        email=email,
        phone=phone,
        banking_account=banking_account,
        bank_name=bank_name,
        sendgrid_api_key=sendgrid_api_key,
        smsportal_client_id=smsportal_client_id,
        smsportal_api_secret=smsportal_api_secret
    )


if __name__ == '__main__':
    main()

