#!/usr/bin/env python3
"""Verify that Amin (user_id 9) is configured correctly for admin access"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def verify_amin():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check Amin's user record
            cur.execute("""
                SELECT user_id, username, email, is_active 
                FROM pharma.users 
                WHERE user_id = 9
            """)
            user = cur.fetchone()
            
            if not user:
                print("❌ ERROR: Amin (user_id 9) not found in database!")
                return False
            
            print("=" * 60)
            print("AMIN USER VERIFICATION")
            print("=" * 60)
            print(f"User ID: {user['user_id']}")
            print(f"Username: {user['username']}")
            print(f"Email: {user['email']}")
            print(f"Active: {user['is_active']}")
            print()
            
            # Check admin configuration in code
            print("=" * 60)
            print("ADMIN CONFIGURATION CHECK")
            print("=" * 60)
            print("Expected admin user IDs: [2, 9]")
            print("  - Charl: user_id 2")
            print("  - Amin: user_id 9")
            print()
            
            # Verify the admin.py file has the correct configuration
            admin_file = Path(__file__).parent.parent / "pharma_api" / "app" / "routers" / "admin.py"
            if admin_file.exists():
                content = admin_file.read_text()
                if "AMIN_USER_ID = 9" in content and "ADMIN_USER_IDS = {CHARL_USER_ID, AMIN_USER_ID}" in content:
                    print("✓ admin.py configuration looks correct")
                else:
                    print("❌ WARNING: admin.py might not have correct Amin configuration")
                    print("   Please verify ADMIN_USER_IDS includes user_id 9")
            
            print()
            print("=" * 60)
            print("TROUBLESHOOTING STEPS")
            print("=" * 60)
            print("1. Make sure the server has been restarted after code changes")
            print("2. Clear browser localStorage (remove 'admin_token')")
            print("3. Log out and log back in as Amin")
            print("4. Verify username is exactly 'Amin' (case-sensitive)")
            print("5. Check browser console for any error messages")
            print()
            
            return True

if __name__ == "__main__":
    try:
        verify_amin()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



