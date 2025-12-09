#!/usr/bin/env python3
"""
Grant write access to all users for all pharmacies they have access to.

This script updates all existing user_pharmacies entries to set can_write = true
for all users who currently have read access.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def grant_write_access_to_all():
    """Grant write access to all users for all their pharmacies"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # First, get all current access records
            cur.execute("""
                SELECT 
                    up.user_id,
                    u.username,
                    up.pharmacy_id,
                    p.name as pharmacy_name,
                    up.can_read,
                    up.can_write
                FROM pharma.user_pharmacies up
                JOIN pharma.users u ON u.user_id = up.user_id
                JOIN pharma.pharmacies p ON p.pharmacy_id = up.pharmacy_id
                ORDER BY up.user_id, up.pharmacy_id
            """)
            
            current_access = cur.fetchall()
            
            if not current_access:
                print("No pharmacy access records found.")
                return
            
            print("=" * 80)
            print("GRANTING WRITE ACCESS TO ALL USERS")
            print("=" * 80)
            print(f"\nFound {len(current_access)} access record(s) to update.\n")
            
            # Update all records to have write access
            updated_count = 0
            skipped_count = 0
            
            for record in current_access:
                user_id = record['user_id']
                username = record['username']
                pharmacy_id = record['pharmacy_id']
                pharmacy_name = record['pharmacy_name']
                current_write = record['can_write']
                
                if current_write:
                    print(f"  ⏭️  {username} (ID: {user_id}) already has write access to {pharmacy_name} (ID: {pharmacy_id})")
                    skipped_count += 1
                    continue
                
                # Update to grant write access
                cur.execute("""
                    UPDATE pharma.user_pharmacies
                    SET can_write = true
                    WHERE user_id = %s AND pharmacy_id = %s
                """, (user_id, pharmacy_id))
                
                print(f"  ✓ Granted write access to {username} (ID: {user_id}) for {pharmacy_name} (ID: {pharmacy_id})")
                updated_count += 1
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"  Updated: {updated_count} access record(s)")
            print(f"  Skipped: {skipped_count} access record(s) (already had write access)")
            print(f"  Total:   {len(current_access)} access record(s)")
            print("=" * 80)
            
            # Show final state
            print("\nFinal access summary by user:")
            cur.execute("""
                SELECT 
                    u.user_id,
                    u.username,
                    COUNT(up.pharmacy_id) as pharmacy_count,
                    COUNT(CASE WHEN up.can_write THEN 1 END) as write_count
                FROM pharma.users u
                LEFT JOIN pharma.user_pharmacies up ON up.user_id = u.user_id
                GROUP BY u.user_id, u.username
                ORDER BY u.user_id
            """)
            
            users_summary = cur.fetchall()
            print("-" * 80)
            for user in users_summary:
                pharmacy_count = user['pharmacy_count'] or 0
                write_count = user['write_count'] or 0
                print(f"  {user['username']} (ID: {user['user_id']}): "
                      f"{pharmacy_count} pharmacy(ies), {write_count} with write access")

if __name__ == "__main__":
    try:
        grant_write_access_to_all()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



