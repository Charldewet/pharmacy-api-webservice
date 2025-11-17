"""
Complete PDF Parser for Debtor Reminder System

This module extracts debtor account information from PDF reports.
It handles account numbers, names, ageing buckets, balances, and contact information.

Author: Debtor Reminder System
Date: 2025-01-16
"""

import re
import fitz  # PyMuPDF
import pandas as pd
from typing import List, Dict, Optional


def is_medical_aid_control_account(name: str) -> bool:
    """
    Check if an account name matches medical aid control account patterns.
    
    Args:
        name: Account name to check
        
    Returns:
        True if the name matches medical aid control patterns, False otherwise
    """
    if not name:
        return False
    
    name_upper = name.upper().strip()
    
    # Medical aid control account patterns
    medical_aid_patterns = [
        'MEDAID CONTROL ACC',
        'MEDICAL AID CONTROL',
        'MEDICAL AID CONTROL ACCOUNT',
        'MED AID CONTROL',
        'MEDAID CONTROL',
        'MEDICAL AID ACC',
        'MEDICAL AID',
        'MEDAID',
    ]
    
    return any(pattern in name_upper for pattern in medical_aid_patterns)


def clean_name(name_section: str) -> str:
    """
    Clean and extract customer name from raw name section.
    Removes titles, numbers, and invalid patterns.
    
    Args:
        name_section: Raw name section from PDF line
        
    Returns:
        Cleaned name string
    """
    # Common title prefixes to remove
    title_prefixes = {
        "MR", "MRS", "MISS", "MS", "DR", "PROF", "MEV", "MNR", "ME",
        "MR.", "MRS.", "MISS.", "MS.", "DR.", "PROF.", "MEV.", "MNR.", "ME."
    }
    
    # Normalize whitespace
    name_section = re.sub(r"\s{2,}", " ", name_section).strip()
    raw_name_parts = name_section.split()
    
    # Remove titles and invalid patterns
    clean_name_parts = []
    for part in raw_name_parts:
        upper_part = part.upper().strip()
        
        # Skip titles
        if upper_part in title_prefixes:
            continue
        
        # Skip pure numbers
        if re.match(r"^-?\d+\.?\d*$", part):
            continue
        
        # Skip ".00" or patterns starting with "."
        if part == ".00" or (part.startswith(".") and len(part) <= 3):
            continue
        
        # Skip empty parts
        if not part:
            continue
        
        clean_name_parts.append(part)
    
    name = " ".join(clean_name_parts)
    return name.strip()


def extract_email_from_line(line: str) -> Optional[str]:
    """
    Extract email address from a line of text.
    
    Args:
        line: Text line to search for email
        
    Returns:
        Email address if found, None otherwise
    """
    if not line or "email" not in line.lower():
        return None
    
    # Email pattern: word characters, dots, hyphens, @ symbol, domain
    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    email_match = re.search(email_pattern, line)
    
    if email_match:
        return email_match.group().strip()
    
    return None


def extract_phone_from_line(line: str) -> Optional[str]:
    """
    Extract South African phone number from a line of text.
    Supports formats: +27XXXXXXXXX or 0XXXXXXXXX
    
    Args:
        line: Text line to search for phone number
        
    Returns:
        Phone number if found, None otherwise
    """
    if not line:
        return None
    
    # Check if line contains phone indicators
    phone_indicators = ['tel', 'phone', 'cell', 'mobile', 'contact']
    has_indicator = any(indicator in line.lower() for indicator in phone_indicators)
    
    if not has_indicator:
        return None
    
    # Remove all spaces and special characters except + and digits
    digits_line = re.sub(r'[^\d+]', '', line)
    
    # South African phone pattern:
    # +27 followed by 9 digits (mobile starts with 6-8)
    # OR 0 followed by 9 digits (mobile starts with 6-8)
    phone_patterns = [
        r'\+27[6-8]\d{8}',  # +27 format
        r'0[6-8]\d{8}',      # 0 format
    ]
    
    for pattern in phone_patterns:
        phone_match = re.search(pattern, digits_line)
        if phone_match:
            return phone_match.group()
    
    return None


def parse_ageing_buckets(fields: List[str]) -> tuple:
    """
    Parse ageing bucket values from field list.
    Expects 8 values: current, d30, d60, d90, d120, d150, d180, balance
    
    Args:
        fields: List of string values representing amounts
        
    Returns:
        Tuple of 8 float values: (current, d30, d60, d90, d120, d150, d180, balance)
    """
    buckets = []
    
    for idx in range(8):
        if idx < len(fields):
            # Remove commas and convert to float
            val = fields[idx].replace(",", "").replace(" ", "")
            try:
                buckets.append(float(val))
            except (ValueError, AttributeError):
                buckets.append(0.0)
        else:
            buckets.append(0.0)
    
    return tuple(buckets)


def extract_debtors_strictest_names(pdf_path: str) -> pd.DataFrame:
    """
    Extract debtor account information from PDF report.
    
    This function:
    1. Opens and reads PDF file
    2. Identifies account lines (starting with 6-digit account number)
    3. Extracts account number, name, ageing buckets, and balance
    4. Looks ahead for email and phone information
    5. Filters out invalid accounts and medical aid control accounts
    6. Returns structured data as pandas DataFrame
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        pandas DataFrame with columns:
        - acc_no: Account number (string)
        - name: Customer name (string)
        - current: Current balance (float)
        - d30: 30 days overdue (float)
        - d60: 60 days overdue (float)
        - d90: 90 days overdue (float)
        - d120: 120 days overdue (float)
        - d150: 150 days overdue (float)
        - d180: 180 days overdue (float)
        - balance: Total outstanding balance (float)
        - email: Email address (string, may be empty)
        - phone: Phone number (string, may be empty)
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        Exception: For other parsing errors
    """
    try:
        # Open PDF document
        doc = fitz.open(pdf_path)
        
        # Extract all text lines from all pages
        lines = []
        for page in doc:
            page_lines = page.get_text().splitlines()
            lines.extend(page_lines)
        
        doc.close()
        
        # Storage for extracted debtor data
        data = []
        
        # Process each line
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Identify account lines: must start with exactly 6 digits followed by space
            if not re.match(r"^\d{6}\s", line):
                continue
            
            try:
                # Extract account number (first 6 digits)
                acc_no = line[:6].strip()
                
                # Get rest of line after account number
                rest = line[6:].strip()
                
                # Find the start of the first number (ageing bucket values)
                # Look for patterns like "100.00" or ".00" or "-100.00"
                first_number_match = re.search(r"-?\d+\.\d{2}|\.00|-?\d+\.\d{1,2}", rest)
                
                if not first_number_match:
                    # No numbers found, skip this line
                    continue
                
                # Extract name section (everything before the first number)
                name_section = rest[:first_number_match.start()].strip()
                
                # Clean the name
                name = clean_name(name_section)
                
                # Validate name: must contain at least one letter
                if not re.search(r"[a-zA-Z]", name):
                    continue
                
                # Skip medical aid control accounts
                if is_medical_aid_control_account(name):
                    continue
                
                # Extract ageing bucket values
                # Everything after the name section
                after_name = rest[first_number_match.start():].strip()
                fields = after_name.split()
                
                # Parse the 8 ageing bucket values
                current, d30, d60, d90, d120, d150, d180, balance = parse_ageing_buckets(fields)
                
                # Initialize contact information
                email = ""
                phone = ""
                
                # Look ahead 1-4 lines for email and phone information
                for j in range(1, 5):
                    if i + j >= len(lines):
                        break
                    
                    next_line = lines[i + j].strip()
                    
                    # Skip empty lines
                    if not next_line:
                        continue
                    
                    # Extract email if not already found
                    if not email:
                        extracted_email = extract_email_from_line(next_line)
                        if extracted_email:
                            email = extracted_email
                    
                    # Extract phone if not already found
                    if not phone:
                        extracted_phone = extract_phone_from_line(next_line)
                        if extracted_phone:
                            phone = extracted_phone
                    
                    # Stop looking if we've found both
                    if email and phone:
                        break
                    
                    # Stop looking if we encounter another account line
                    if re.match(r"^\d{6}\s", next_line):
                        break
                
                # Create debtor record
                debtor_record = {
                    "acc_no": acc_no,
                    "name": name,
                    "current": current,
                    "d30": d30,
                    "d60": d60,
                    "d90": d90,
                    "d120": d120,
                    "d150": d150,
                    "d180": d180,
                    "balance": balance,
                    "email": email,
                    "phone": phone
                }
                
                data.append(debtor_record)
                
            except Exception as e:
                # Log error but continue processing other accounts
                print(f"Error processing line {i}: {str(e)}")
                print(f"Line content: {line[:100]}...")
                continue
        
        # Convert to DataFrame
        if not data:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=[
                "acc_no", "name", "current", "d30", "d60", "d90", 
                "d120", "d150", "d180", "balance", "email", "phone"
            ])
        
        df = pd.DataFrame(data)
        
        # Ensure data types are correct
        numeric_columns = ["current", "d30", "d60", "d90", "d120", "d150", "d180", "balance"]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # Ensure string columns are strings
        df["acc_no"] = df["acc_no"].astype(str)
        df["name"] = df["name"].astype(str)
        df["email"] = df["email"].astype(str)
        df["phone"] = df["phone"].astype(str)
        
        return df
        
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")


def extract_debtors_with_medical_aid_flag(pdf_path: str) -> pd.DataFrame:
    """
    Extract debtor information including medical aid control flag.
    
    This is an enhanced version that includes a flag for medical aid accounts
    instead of filtering them out. Useful for reporting purposes.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        pandas DataFrame with additional 'is_medical_aid_control' column
    """
    df = extract_debtors_strictest_names(pdf_path)
    
    # Add medical aid flag
    df['is_medical_aid_control'] = df['name'].apply(is_medical_aid_control_account)
    
    return df


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python PDF_PARSER_COMPLETE.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    try:
        print(f"Parsing PDF: {pdf_file}")
        df = extract_debtors_strictest_names(pdf_file)
        
        print(f"\nExtracted {len(df)} debtor accounts")
        print("\nFirst few records:")
        print(df.head())
        
        print("\nSummary statistics:")
        print(f"Total accounts: {len(df)}")
        print(f"Total outstanding: R {df['balance'].sum():,.2f}")
        print(f"Accounts with email: {df[df['email'] != ''].shape[0]}")
        print(f"Accounts with phone: {df[df['phone'] != ''].shape[0]}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
