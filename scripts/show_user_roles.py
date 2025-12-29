#!/usr/bin/env python3
"""
Display all users and their roles in a formatted table.
"""

import sys
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def show_user_roles():
    """Display all users with their roles"""
    with get_conn() as conn, conn.cursor() as cur:
        # Get all users with their roles and pharmacy access
        cur.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.email,
                u.is_active,
                u.is_admin,
                u.is_accounting,
                COUNT(up.pharmacy_id) as pharmacy_count,
                COUNT(up.pharmacy_id) FILTER (WHERE up.can_write = true) as write_pharmacy_count
            FROM pharma.users u
            LEFT JOIN pharma.user_pharmacies up ON up.user_id = u.user_id
            GROUP BY u.user_id, u.username, u.email, u.is_active, u.is_admin, u.is_accounting
            ORDER BY u.user_id
        """)
        
        users = cur.fetchall()
        
        print("=" * 100)
        print("USER ROLES SUMMARY")
        print("=" * 100)
        print()
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Active':<8} {'Admin':<8} {'Accounting':<12} {'Pharmacies':<12}")
        print("-" * 100)
        
        for user in users:
            roles = []
            if user['is_admin']:
                roles.append("Admin")
            if user['is_accounting']:
                roles.append("Accounting")
            if not roles:
                roles.append("Standard")
            
            role_str = ", ".join(roles)
            
            active_str = "✓" if user['is_active'] else "✗"
            admin_str = "✓" if user['is_admin'] else "✗"
            accounting_str = "✓" if user['is_accounting'] else "✗"
            
            pharmacy_info = f"{user['pharmacy_count']} total"
            if user['write_pharmacy_count'] > 0:
                pharmacy_info += f" ({user['write_pharmacy_count']} write)"
            
            print(f"{user['user_id']:<5} {user['username']:<20} {user['email']:<30} {active_str:<8} {admin_str:<8} {accounting_str:<12} {pharmacy_info:<12}")
        
        print()
        print("=" * 100)
        print("ROLE BREAKDOWN")
        print("=" * 100)
        
        # Count users by role
        admin_count = sum(1 for u in users if u['is_admin'])
        accounting_count = sum(1 for u in users if u['is_accounting'])
        both_count = sum(1 for u in users if u['is_admin'] and u['is_accounting'])
        standard_count = sum(1 for u in users if not u['is_admin'] and not u['is_accounting'])
        
        print(f"Admin users: {admin_count}")
        print(f"Accounting users: {accounting_count}")
        print(f"Users with both roles: {both_count}")
        print(f"Standard users (no special roles): {standard_count}")
        print(f"Total users: {len(users)}")
        print()

if __name__ == "__main__":
    show_user_roles()

