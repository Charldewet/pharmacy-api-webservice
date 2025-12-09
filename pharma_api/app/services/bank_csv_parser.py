"""
Bank CSV Parser
Parses CSV files from banks into standardized format.
Based on Ruby implementation for consistency.
"""

import csv
import io
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation
try:
    from dateutil import parser as date_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False


class ParsedRow:
    """Represents a successfully parsed CSV row"""
    def __init__(self, row_number: int, date: date, description: str, 
                 raw_description: str, reference: Optional[str], 
                 amount: Decimal, balance: Optional[Decimal], raw_data: Dict):
        self.row_number = row_number
        self.date = date
        self.description = description
        self.raw_description = raw_description
        self.reference = reference
        self.amount = amount
        self.balance = balance
        self.raw_data = raw_data


class ParseError:
    """Represents a parsing error for a CSV row"""
    def __init__(self, row_number: int, error: str, raw_data: Dict):
        self.row_number = row_number
        self.error = error
        self.raw_data = raw_data


class ParseResult:
    """Result of parsing a CSV file"""
    def __init__(self, rows: List[ParsedRow], errors: List[ParseError], summary: Dict):
        self.rows = rows
        self.errors = errors
        self.summary = summary


class BankCsvParser:
    """Parser for bank CSV files"""
    
    @staticmethod
    def parse(file_content: bytes) -> ParseResult:
        """
        Parse a CSV file.
        
        Args:
            file_content: Raw CSV file bytes
        
        Returns:
            ParseResult with rows, errors, and summary
        """
        parser = BankCsvParser(file_content)
        return parser._parse()
    
    def __init__(self, file_content: bytes):
        self.file_content = file_content
    
    def _parse(self) -> ParseResult:
        """Main parsing logic"""
        rows = []
        errors = []
        
        row_number = 0
        total_in = Decimal("0")
        total_out = Decimal("0")
        min_date = None
        max_date = None
        
        csv_enum = self._csv_enum()
        
        for raw_row in csv_enum:
            row_number += 1
            
            # Skip completely empty rows
            if self._is_empty_row(raw_row):
                continue
            
            try:
                parsed = self._parse_row(row_number, raw_row)
                rows.append(parsed)
                
                # Update totals
                if parsed.amount > 0:
                    total_in += parsed.amount
                elif parsed.amount < 0:
                    total_out += parsed.amount
                
                # Update period range
                if min_date is None or parsed.date < min_date:
                    min_date = parsed.date
                if max_date is None or parsed.date > max_date:
                    max_date = parsed.date
                    
            except Exception as e:
                errors.append(ParseError(
                    row_number=row_number,
                    error=str(e),
                    raw_data=dict(raw_row)
                ))
        
        summary = {
            "transaction_count": len(rows),
            "total_in": float(total_in),
            "total_out": float(total_out),
            "min_date": min_date.isoformat() if min_date else None,
            "max_date": max_date.isoformat() if max_date else None
        }
        
        return ParseResult(rows=rows, errors=errors, summary=summary)
    
    def _csv_enum(self):
        """Create CSV reader with proper encoding and separator detection"""
        # Decode file content
        try:
            content = self.file_content.decode('utf-8-sig')  # Handle BOM
        except UnicodeDecodeError:
            try:
                content = self.file_content.decode('latin-1')
            except UnicodeDecodeError:
                raise ValueError("Unable to decode file. Expected UTF-8 or Latin-1 encoding.")
        
        # Detect separator
        delimiter = self._detect_separator(content)
        
        # Create CSV reader
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        return reader
    
    def _detect_separator(self, content: str) -> str:
        """Detect CSV separator (comma or semicolon)"""
        first_line = content.split('\n')[0] if content else ""
        if first_line.count(';') > first_line.count(','):
            return ';'
        return ','
    
    def _is_empty_row(self, row: Dict) -> bool:
        """Check if row is completely empty"""
        return all(not v or str(v).strip() == '' for v in row.values())
    
    def _parse_row(self, row_number: int, row: Dict) -> ParsedRow:
        """Parse a single CSV row"""
        # Case-insensitive field access
        row_lower = {k.lower(): v for k, v in row.items()}
        
        date_str = row_lower.get('date') or row.get('Date') or row.get('date')
        description_str = row_lower.get('description') or row.get('Description') or row.get('description')
        amount_str = row_lower.get('amount') or row.get('Amount') or row.get('amount')
        balance_str = row_lower.get('balance') or row.get('Balance')
        reference_str = row_lower.get('reference') or row.get('Reference')
        
        # Validate required fields
        if not date_str or str(date_str).strip() == '':
            raise ValueError("Missing Date")
        if not description_str or str(description_str).strip() == '':
            raise ValueError("Missing Description")
        if amount_str is None or str(amount_str).strip() == '':
            raise ValueError("Missing Amount")
        
        # Parse fields
        parsed_date = self._parse_date(str(date_str))
        parsed_amount = self._parse_amount(str(amount_str))
        parsed_balance = self._parse_amount(str(balance_str)) if balance_str and str(balance_str).strip() else None
        
        return ParsedRow(
            row_number=row_number,
            date=parsed_date,
            description=self._normalize_description(str(description_str)),
            raw_description=str(description_str),
            reference=str(reference_str).strip() if reference_str else None,
            amount=parsed_amount,
            balance=parsed_balance,
            raw_data=dict(row)
        )
    
    def _parse_date(self, date_str: str) -> date:
        """
        Parse date string. Tries DD/MM/YYYY first (most common in SA),
        then falls back to other formats.
        """
        s = date_str.strip()
        
        # Try DD/MM/YYYY first (most common in South Africa)
        formats = [
            '%d/%m/%Y',      # 29/11/2025
            '%d-%m-%Y',      # 29-11-2025
            '%Y-%m-%d',      # 2025-11-29 (ISO)
            '%Y/%m/%d',      # 2025/11/29
            '%d/%m/%y',      # 29/11/25
            '%d-%m-%y',      # 29-11-25
            '%d.%m.%Y',      # 29.11.2025
            '%Y.%m.%d',      # 2025.11.29
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.date()
            except ValueError:
                continue
        
        # If dateutil is available, try flexible parsing
        if DATEUTIL_AVAILABLE:
            try:
                dt = date_parser.parse(s, dayfirst=True)  # Prefer DD/MM/YYYY
                return dt.date()
            except (ValueError, TypeError, OverflowError):
                pass
        
        # Try regex-based parsing for DD/MM/YYYY
        match = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', s)
        if match:
            day, month, year = match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                pass
        
        raise ValueError(f"Invalid date format: {s}")
    
    def _parse_amount(self, amount_str: str) -> Decimal:
        """
        Parse amount string. Handles various formats including commas, spaces, etc.
        """
        s = str(amount_str).strip()
        
        # Remove spaces
        s = s.replace(' ', '')
        
        # Remove currency symbols
        s = s.replace('R', '').replace('ZAR', '').replace('$', '').replace('€', '').replace('£', '')
        
        # Handle thousands separators
        # If there's a comma before the last 3 digits, it's likely a thousands separator
        # e.g., "1,234.56" -> "1234.56"
        # But "123,45" (European format) -> "123.45"
        if ',' in s and '.' in s:
            # Has both comma and dot - assume comma is thousands separator
            s = s.replace(',', '')
        elif ',' in s:
            # Only comma - could be decimal separator (European) or thousands separator
            # Check position: if comma is in last 3 chars, it's likely decimal
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Likely European decimal format: "123,45"
                s = s.replace(',', '.')
            else:
                # Likely thousands separator: "1,234"
                s = s.replace(',', '')
        
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid amount: {amount_str}")
    
    def _normalize_description(self, desc_str: str) -> str:
        """Normalize description: trim, collapse spaces, uppercase"""
        s = str(desc_str).strip()
        # Collapse multiple spaces to single space
        s = re.sub(r'\s+', ' ', s)
        return s.upper()

