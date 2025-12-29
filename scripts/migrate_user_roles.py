#!/usr/bin/env python3
"""
Migration script to add is_admin and is_accounting columns to users table.

This script:
1. Adds is_admin and is_accounting columns to pharma.users table
2. Sets is_admin=true for existing admin users (user_id 2 and 9)
3. Verifies the migration
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def migrate_user_roles():
    """Add role columns to users table and set admin users"""
    print("Starting user roles migration...")
    
    with get_conn() as conn, conn.cursor() as cur:
        try:
            # Check if columns already exist
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'pharma' 
                AND table_name = 'users' 
                AND column_name IN ('is_admin', 'is_accounting')
            """)
            existing_columns = {row['column_name'] for row in cur.fetchall()}
            
            # Add is_admin column if it doesn't exist
            if 'is_admin' not in existing_columns:
                print("Adding is_admin column...")
                cur.execute("""
                    ALTER TABLE pharma.users 
                    ADD COLUMN is_admin boolean NOT NULL DEFAULT false
                """)
                print("✓ Added is_admin column")
            else:
                print("✓ is_admin column already exists")
            
            # Add is_accounting column if it doesn't exist
            if 'is_accounting' not in existing_columns:
                print("Adding is_accounting column...")
                cur.execute("""
                    ALTER TABLE pharma.users 
                    ADD COLUMN is_accounting boolean NOT NULL DEFAULT false
                """)
                print("✓ Added is_accounting column")
            else:
                print("✓ is_accounting column already exists")
            
            # Set admin users (user_id 2 and 9)
            print("\nSetting admin users...")
            ADMIN_USER_IDS = [2, 9]
            for user_id in ADMIN_USER_IDS:
                cur.execute("""
                    UPDATE pharma.users 
                    SET is_admin = true 
                    WHERE user_id = %s
                """, (user_id,))
                if cur.rowcount > 0:
                    print(f"✓ Set user_id {user_id} as admin")
                else:
                    print(f"⚠ User_id {user_id} not found (may not exist yet)")
            
            conn.commit()
            
            # Verify migration
            print("\nVerifying migration...")
            cur.execute("""
                SELECT 
                    user_id,
                    username,
                    is_admin,
                    is_accounting
                FROM pharma.users
                ORDER BY user_id
            """)
            
            users = cur.fetchall()
            print(f"\nFound {len(users)} users:")
            for user in users:
                roles = []
                if user['is_admin']:
                    roles.append("admin")
                if user['is_accounting']:
                    roles.append("accounting")
                role_str = ", ".join(roles) if roles else "none"
                print(f"  User {user['user_id']} ({user['username']}): {role_str}")
            
            print("\n✓ Migration completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"\n✗ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_user_roles()

