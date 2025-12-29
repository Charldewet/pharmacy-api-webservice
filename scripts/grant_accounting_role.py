#!/usr/bin/env python3
"""
Grant accounting role to a user.
"""

import sys
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def grant_accounting_role(user_id: int):
    """Grant accounting role to a user"""
    with get_conn() as conn, conn.cursor() as cur:
        # Check if user exists
        cur.execute("""
            SELECT user_id, username, email, is_admin, is_accounting
            FROM pharma.users
            WHERE user_id = %s
        """, (user_id,))
        
        user = cur.fetchone()
        if not user:
            print(f"❌ User ID {user_id} not found!")
            return False
        
        print(f"Current user: {user['username']} (ID: {user['user_id']})")
        print(f"  Email: {user['email']}")
        print(f"  Admin: {'Yes' if user['is_admin'] else 'No'}")
        print(f"  Accounting: {'Yes' if user['is_accounting'] else 'No'}")
        print()
        
        if user['is_accounting']:
            print(f"✓ User {user['username']} already has accounting role")
            return True
        
        # Grant accounting role
        cur.execute("""
            UPDATE pharma.users
            SET is_accounting = true
            WHERE user_id = %s
        """, (user_id,))
        
        conn.commit()
        
        print(f"✓ Successfully granted accounting role to {user['username']}")
        
        # Show updated roles
        cur.execute("""
            SELECT is_admin, is_accounting
            FROM pharma.users
            WHERE user_id = %s
        """, (user_id,))
        
        updated = cur.fetchone()
        print()
        print("Updated roles:")
        print(f"  Admin: {'Yes' if updated['is_admin'] else 'No'}")
        print(f"  Accounting: {'Yes' if updated['is_accounting'] else 'No'}")
        
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    else:
        # Default to Charl (user_id 2)
        user_id = 2
    
    grant_accounting_role(user_id)

