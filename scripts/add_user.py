#!/usr/bin/env python3
"""
Add a new user to the pharmacy system.

Usage:
    python scripts/add_user.py --username Christo --password Christo1 --email christo@example.com
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import hashlib
from src.db.conn import get_conn

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (same as the app)"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def add_user(username: str, password: str, email: str) -> int:
    """Add a new user to the system"""
    password_hash = hash_password(password)
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check if user already exists
            cur.execute(
                "SELECT user_id, username FROM pharma.users WHERE username = %s OR email = %s",
                (username, email)
            )
            existing = cur.fetchone()
            if existing:
                if existing['username'] == username:
                    raise ValueError(f"Username '{username}' already exists")
                else:
                    raise ValueError(f"Email '{email}' already exists")
            
            # Insert new user
            cur.execute(
                """
                INSERT INTO pharma.users (username, email, password_hash, is_active)
                VALUES (%s, %s, %s, true)
                RETURNING user_id
                """,
                (username, email, password_hash)
            )
            user_id = cur.fetchone()['user_id']
            conn.commit()
            
            print(f"✓ User created successfully!")
            print(f"  User ID: {user_id}")
            print(f"  Username: {username}")
            print(f"  Email: {email}")
            print(f"  Status: Active")
            
            return user_id

def grant_pharmacy_access(user_id: int, pharmacy_id: int, can_read: bool = True, can_write: bool = False):
    """Grant pharmacy access to a user"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check if pharmacy exists
            cur.execute(
                "SELECT pharmacy_id, name FROM pharma.pharmacies WHERE pharmacy_id = %s",
                (pharmacy_id,)
            )
            pharmacy = cur.fetchone()
            if not pharmacy:
                raise ValueError(f"Pharmacy ID {pharmacy_id} not found")
            
            # Grant access
            cur.execute(
                """
                INSERT INTO pharma.user_pharmacies (user_id, pharmacy_id, can_read, can_write)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, pharmacy_id) DO UPDATE SET
                    can_read = EXCLUDED.can_read,
                    can_write = EXCLUDED.can_write
                """,
                (user_id, pharmacy_id, can_read, can_write)
            )
            conn.commit()
            
            access_type = []
            if can_read:
                access_type.append("READ")
            if can_write:
                access_type.append("WRITE")
            
            print(f"✓ Granted access to {pharmacy['name']} (ID: {pharmacy_id})")
            print(f"  Permissions: {', '.join(access_type)}")

def list_available_pharmacies():
    """List all available pharmacies"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pharmacy_id, name, is_active FROM pharma.pharmacies ORDER BY pharmacy_id"
            )
            pharmacies = cur.fetchall()
            
            print("\nAvailable Pharmacies:")
            print("=" * 60)
            for p in pharmacies:
                status = "ACTIVE" if p['is_active'] else "INACTIVE"
                print(f"  ID {p['pharmacy_id']}: {p['name']} ({status})")
            
            return pharmacies

def main():
    parser = argparse.ArgumentParser(
        description="Add a new user to the pharmacy system"
    )
    parser.add_argument("--username", help="Username for the new user")
    parser.add_argument("--password", help="Password for the new user")
    parser.add_argument("--email", help="Email address for the new user")
    parser.add_argument(
        "--pharmacy-ids", 
        type=str, 
        help="Comma-separated list of pharmacy IDs to grant access to (e.g., '1,2,101')"
    )
    parser.add_argument(
        "--can-write", 
        action="store_true", 
        help="Grant write access to pharmacies (default: read-only)"
    )
    parser.add_argument(
        "--list-pharmacies", 
        action="store_true", 
        help="List available pharmacies and exit"
    )
    
    args = parser.parse_args()
    
    if args.list_pharmacies:
        list_available_pharmacies()
        return
    
    # Check required arguments for user creation
    if not args.username or not args.password or not args.email:
        parser.error("--username, --password, and --email are required unless using --list-pharmacies")
    
    print("=" * 60)
    print("ADDING NEW USER TO PHARMACY SYSTEM")
    print("=" * 60)
    
    try:
        # Add the user
        user_id = add_user(args.username, args.password, args.email)
        
        # Grant pharmacy access if specified
        if args.pharmacy_ids:
            print(f"\nGranting pharmacy access...")
            pharmacy_ids = [int(pid.strip()) for pid in args.pharmacy_ids.split(',')]
            
            for pharmacy_id in pharmacy_ids:
                try:
                    grant_pharmacy_access(user_id, pharmacy_id, can_read=True, can_write=args.can_write)
                except ValueError as e:
                    print(f"  ⚠️  Warning: {e}")
        else:
            print(f"\nNo pharmacy access granted. Use the API or run this script again with --pharmacy-ids to grant access.")
            print(f"Available pharmacies:")
            list_available_pharmacies()
        
        print(f"\n" + "=" * 60)
        print(f"✓ USER SETUP COMPLETE!")
        print(f"=" * 60)
        print(f"The user '{args.username}' can now log in to the app with:")
        print(f"  Username: {args.username}")
        print(f"  Password: {args.password}")
        
        if args.pharmacy_ids:
            access_type = "read/write" if args.can_write else "read-only"
            print(f"  Access: {access_type} access to {len(pharmacy_ids)} pharmacy(ies)")
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 