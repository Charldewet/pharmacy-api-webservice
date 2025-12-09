"""
Bank CSV Parsers
Parses CSV files from different South African banks into standardized format.
"""

import csv
import io
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation
try:
    from dateutil import parser as date_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False


class BankParseResult:
    """Result of parsing a single CSV row"""
    def __init__(self):
        self.date: Optional[str] = None
        self.description: Optional[str] = None
        self.reference: Optional[str] = None
        self.amount: Optional[Decimal] = None
        self.balance: Optional[Decimal] = None
        self.external_id: Optional[str] = None  # Unique transaction ID from bank
        self.raw_data: Optional[Dict] = None
        self.error: Optional[str] = None


class BankParser:
    """Base class for bank CSV parsers"""
    
    def parse_row(self, row: Dict[str, str], row_number: int) -> BankParseResult:
        """Parse a single CSV row into standardized format"""
        result = BankParseResult()
        result.raw_data = row
        
        try:
            # Extract and validate required fields
            result.date = self._parse_date(row)
            result.description = self._normalize_description(row)
            result.reference = self._parse_reference(row)
            result.amount = self._parse_amount(row)
            result.balance = self._parse_balance(row)
            result.external_id = self._parse_external_id(row)
            
            # Validate required fields
            if not result.date:
                result.error = "Missing or invalid date"
            elif not result.description:
                result.error = "Missing description"
            elif result.amount is None:
                result.error = "Missing or invalid amount"
            
        except Exception as e:
            result.error = f"Parse error: {str(e)}"
        
        return result
    
    def _parse_date(self, row: Dict[str, str]) -> Optional[str]:
        """Parse date field - must be implemented by subclasses"""
        raise NotImplementedError
    
    def _normalize_description(self, row: Dict[str, str]) -> Optional[str]:
        """Extract and normalize description"""
        desc = self._get_description(row)
        if desc:
            # Normalize: trim, collapse spaces, uppercase
            desc = ' '.join(desc.split()).upper()
        return desc
    
    def _get_description(self, row: Dict[str, str]) -> Optional[str]:
        """Get description field - must be implemented by subclasses"""
        raise NotImplementedError
    
    def _parse_reference(self, row: Dict[str, str]) -> Optional[str]:
        """Extract reference field - optional"""
        return None
    
    def _parse_amount(self, row: Dict[str, str]) -> Optional[Decimal]:
        """Parse amount field - must be implemented by subclasses"""
        raise NotImplementedError
    
    def _parse_balance(self, row: Dict[str, str]) -> Optional[Decimal]:
        """Parse balance field - optional"""
        return None
    
    def _parse_external_id(self, row: Dict[str, str]) -> Optional[str]:
        """Extract external/unique transaction ID - optional, implemented by subclasses"""
        # Common field names across banks
        external_id_fields = [
            'Transaction ID', 'TransactionID', 'TransactionId',
            'Unique Reference', 'UniqueReference', 'Unique Ref',
            'External ID', 'ExternalID', 'ExternalId',
            'Reference Number', 'ReferenceNumber', 'Ref Number',
            'Trace Number', 'TraceNumber', 'Trace No',
            'Sequence Number', 'SequenceNumber', 'Seq No'
        ]
        
        for field in external_id_fields:
            if field in row and row[field]:
                value = row[field].strip()
                if value:
                    return value
        
        return None
    
    @staticmethod
    def _parse_decimal(value: str) -> Optional[Decimal]:
        """Parse decimal value, handling various formats"""
        if not value or value.strip() == '':
            return None
        
        # Remove currency symbols, spaces, and common separators
        cleaned = value.replace('R', '').replace('ZAR', '').replace(' ', '').replace(',', '')
        
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None
    
    @staticmethod
    def _find_field_case_insensitive(row: Dict[str, str], field_names: List[str]) -> Optional[str]:
        """Find a field in row using case-insensitive matching"""
        row_lower = {k.lower(): v for k, v in row.items()}
        for field in field_names:
            field_lower = field.lower()
            if field_lower in row_lower and row_lower[field_lower]:
                return row_lower[field_lower]
        return None
    
    @staticmethod
    def _parse_date_string(date_str: str, formats: List[str]) -> Optional[str]:
        """Try parsing date string with multiple formats"""
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        # Try explicit formats first
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If dateutil is available, try flexible parsing as fallback
        if DATEUTIL_AVAILABLE:
            try:
                dt = date_parser.parse(date_str, dayfirst=True)  # dayfirst=True for DD/MM/YYYY preference
                return dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError, OverflowError):
                pass
        
        # Try some common variations manually
        # Handle dates like "29/11/2025" or "29-11-2025"
        date_patterns = [
            (r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', '%d/%m/%Y'),  # DD/MM/YYYY or DD-MM-YYYY
            (r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', '%Y/%m/%d'),  # YYYY/MM/DD or YYYY-MM-DD
            (r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$', '%d/%m/%y'),   # DD/MM/YY or DD-MM-YY
        ]
        
        for pattern, fmt_template in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    # Normalize separator
                    normalized = date_str.replace('-', '/')
                    # Try parsing with the template format
                    if '/' in normalized:
                        parts = normalized.split('/')
                        if len(parts) == 3:
                            if fmt_template == '%d/%m/%Y':
                                day, month, year = parts
                            elif fmt_template == '%Y/%m/%d':
                                year, month, day = parts
                            else:  # %d/%m/%y
                                day, month, year = parts
                                year = '20' + year if len(year) == 2 else year
                            
                            # Validate and parse
                            dt = datetime(int(year), int(month), int(day))
                            return dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    continue
        
        return None


class FNBParser(BankParser):
    """Parser for FNB bank CSV format"""
    
    def _parse_date(self, row: Dict[str, str]) -> Optional[str]:
        """FNB typically uses formats like: 2025-03-15 or 15/03/2025"""
        date_fields = ['Date', 'Transaction Date', 'Value Date', 'Posting Date', 'Effective Date']
        
        # Try case-insensitive field matching first
        date_str = self._find_field_case_insensitive(row, date_fields)
        if not date_str:
            return None
        
        date_str = date_str.strip()
        if not date_str:
            return None
        
        # Try common formats (order matters - most common first)
        formats = [
            '%d/%m/%Y',      # DD/MM/YYYY (most common in SA)
            '%d-%m-%Y',      # DD-MM-YYYY
            '%Y-%m-%d',      # YYYY-MM-DD (ISO)
            '%Y/%m/%d',      # YYYY/MM/DD
            '%d/%m/%y',      # DD/MM/YY
            '%d-%m-%y',      # DD-MM-YY
            '%d %b %Y',      # DD Mon YYYY
            '%d %B %Y',      # DD Month YYYY
            '%b %d, %Y',     # Mon DD, YYYY
            '%B %d, %Y',     # Month DD, YYYY
            '%d.%m.%Y',      # DD.MM.YYYY
            '%Y.%m.%d',      # YYYY.MM.DD
        ]
        
        parsed = self._parse_date_string(date_str, formats)
        return parsed
    
    def _get_description(self, row: Dict[str, str]) -> Optional[str]:
        """FNB description fields"""
        desc_fields = ['Description', 'Transaction Description', 'Narrative', 'Details']
        
        # Try case-insensitive matching
        desc = self._find_field_case_insensitive(row, desc_fields)
        return desc
    
    def _parse_reference(self, row: Dict[str, str]) -> Optional[str]:
        """FNB reference fields"""
        ref_fields = ['Reference', 'Reference Number', 'Narrative', 'Contra']
        
        for field in ref_fields:
            if field in row and row[field]:
                return row[field].strip()
        
        return None
    
    def _parse_amount(self, row: Dict[str, str]) -> Optional[Decimal]:
        """FNB amount fields - positive for credits, negative for debits"""
        # Try debit/credit fields first (case-insensitive)
        row_lower = {k.lower(): v for k, v in row.items()}
        
        debit = None
        credit = None
        
        if 'debit' in row_lower and row_lower['debit']:
            debit = self._parse_decimal(row_lower['debit'])
        if 'credit' in row_lower and row_lower['credit']:
            credit = self._parse_decimal(row_lower['credit'])
        
        if debit is not None:
            return -abs(debit)  # Negative for debits
        if credit is not None:
            return abs(credit)  # Positive for credits
        
        # Try single amount field (case-insensitive)
        # When there's a single Amount field, preserve the sign as-is
        # (CSV format already encodes: positive = credit, negative = debit)
        amount_fields = ['Amount', 'Transaction Amount']
        for field in amount_fields:
            amount_str = self._find_field_case_insensitive(row, [field])
            if amount_str:
                amount = self._parse_decimal(amount_str)
                if amount is not None:
                    # Preserve the sign - CSV already has correct encoding
                    return amount
        
        # Try explicit debit/credit amount fields
        debit_amount = self._find_field_case_insensitive(row, ['Amount Debit'])
        credit_amount = self._find_field_case_insensitive(row, ['Amount Credit'])
        
        if debit_amount:
            debit = self._parse_decimal(debit_amount)
            if debit is not None:
                return -abs(debit)
        if credit_amount:
            credit = self._parse_decimal(credit_amount)
            if credit is not None:
                return abs(credit)
        
        return None
    
    def _parse_balance(self, row: Dict[str, str]) -> Optional[Decimal]:
        """FNB balance field"""
        balance_fields = ['Balance', 'Running Balance', 'Available Balance']
        
        for field in balance_fields:
            if field in row and row[field]:
                return self._parse_decimal(row[field])
        
        return None


class ABSAParser(BankParser):
    """Parser for ABSA bank CSV format"""
    
    def _parse_date(self, row: Dict[str, str]) -> Optional[str]:
        """ABSA date formats"""
        date_fields = ['Date', 'Transaction Date', 'Posting Date', 'Value Date', 'Effective Date']
        
        # Try case-insensitive field matching first
        date_str = self._find_field_case_insensitive(row, date_fields)
        if not date_str:
            return None
        
        date_str = date_str.strip()
        if not date_str:
            return None
        
        formats = [
            '%d/%m/%Y',      # DD/MM/YYYY (most common in SA)
            '%d-%m-%Y',      # DD-MM-YYYY
            '%Y-%m-%d',      # YYYY-MM-DD (ISO)
            '%Y/%m/%d',      # YYYY/MM/DD
            '%d/%m/%y',      # DD/MM/YY
            '%d-%m-%y',      # DD-MM-YY
            '%d %b %Y',      # DD Mon YYYY
            '%d %B %Y',      # DD Month YYYY
            '%b %d, %Y',     # Mon DD, YYYY
            '%B %d, %Y',     # Month DD, YYYY
            '%d.%m.%Y',      # DD.MM.YYYY
            '%Y.%m.%d',      # YYYY.MM.DD
        ]
        
        parsed = self._parse_date_string(date_str, formats)
        return parsed
    
    def _get_description(self, row: Dict[str, str]) -> Optional[str]:
        """ABSA description fields"""
        desc_fields = ['Description', 'Transaction Description', 'Narrative', 'Details', 'Memo']
        
        # Try case-insensitive matching
        desc = self._find_field_case_insensitive(row, desc_fields)
        return desc
    
    def _parse_reference(self, row: Dict[str, str]) -> Optional[str]:
        """ABSA reference fields"""
        ref_fields = ['Reference', 'Reference Number', 'Narrative', 'Contra', 'Cheque Number']
        
        for field in ref_fields:
            if field in row and row[field]:
                return row[field].strip()
        
        return None
    
    def _parse_amount(self, row: Dict[str, str]) -> Optional[Decimal]:
        """ABSA amount fields"""
        # Try debit/credit fields first (case-insensitive)
        row_lower = {k.lower(): v for k, v in row.items()}
        
        debit = None
        credit = None
        
        if 'debit' in row_lower and row_lower['debit']:
            debit = self._parse_decimal(row_lower['debit'])
        if 'credit' in row_lower and row_lower['credit']:
            credit = self._parse_decimal(row_lower['credit'])
        if 'withdrawal' in row_lower and row_lower['withdrawal']:
            debit = self._parse_decimal(row_lower['withdrawal'])
        if 'deposit' in row_lower and row_lower['deposit']:
            credit = self._parse_decimal(row_lower['deposit'])
        
        if debit is not None:
            return -abs(debit)
        if credit is not None:
            return abs(credit)
        
        # Try single amount field (case-insensitive)
        # When there's a single Amount field, preserve the sign as-is
        # (CSV format already encodes: positive = credit, negative = debit)
        amount_fields = ['Amount', 'Transaction Amount']
        for field in amount_fields:
            amount_str = self._find_field_case_insensitive(row, [field])
            if amount_str:
                amount = self._parse_decimal(amount_str)
                if amount is not None:
                    # Preserve the sign - CSV already has correct encoding
                    return amount
        
        # Try explicit debit/credit amount fields
        debit_amount = self._find_field_case_insensitive(row, ['Amount Debit'])
        credit_amount = self._find_field_case_insensitive(row, ['Amount Credit'])
        
        if debit_amount:
            debit = self._parse_decimal(debit_amount)
            if debit is not None:
                return -abs(debit)
        if credit_amount:
            credit = self._parse_decimal(credit_amount)
            if credit is not None:
                return abs(credit)
        
        return None
    
    def _parse_balance(self, row: Dict[str, str]) -> Optional[Decimal]:
        """ABSA balance field"""
        balance_fields = ['Balance', 'Running Balance', 'Available Balance']
        
        for field in balance_fields:
            if field in row and row[field]:
                return self._parse_decimal(row[field])
        
        return None


class StandardBankParser(BankParser):
    """Parser for Standard Bank CSV format"""
    
    def _parse_date(self, row: Dict[str, str]) -> Optional[str]:
        """Standard Bank date formats"""
        date_fields = ['Date', 'Transaction Date', 'Posting Date', 'Value Date', 'Effective Date']
        
        # Try case-insensitive field matching first
        date_str = self._find_field_case_insensitive(row, date_fields)
        if not date_str:
            return None
        
        date_str = date_str.strip()
        if not date_str:
            return None
        
        formats = [
            '%d/%m/%Y',      # DD/MM/YYYY (most common in SA)
            '%d-%m-%Y',      # DD-MM-YYYY
            '%Y-%m-%d',      # YYYY-MM-DD (ISO)
            '%Y/%m/%d',      # YYYY/MM/DD
            '%d/%m/%y',      # DD/MM/YY
            '%d-%m-%y',      # DD-MM-YY
            '%d %b %Y',      # DD Mon YYYY
            '%d %B %Y',      # DD Month YYYY
            '%b %d, %Y',     # Mon DD, YYYY
            '%B %d, %Y',     # Month DD, YYYY
            '%d.%m.%Y',      # DD.MM.YYYY
            '%Y.%m.%d',      # YYYY.MM.DD
        ]
        
        parsed = self._parse_date_string(date_str, formats)
        return parsed
    
    def _get_description(self, row: Dict[str, str]) -> Optional[str]:
        """Standard Bank description fields"""
        desc_fields = ['Description', 'Transaction Description', 'Narrative', 'Details']
        
        # Try case-insensitive matching
        desc = self._find_field_case_insensitive(row, desc_fields)
        return desc
    
    def _parse_reference(self, row: Dict[str, str]) -> Optional[str]:
        """Standard Bank reference fields"""
        ref_fields = ['Reference', 'Reference Number', 'Narrative']
        
        for field in ref_fields:
            if field in row and row[field]:
                return row[field].strip()
        
        return None
    
    def _parse_amount(self, row: Dict[str, str]) -> Optional[Decimal]:
        """Standard Bank amount fields"""
        # Try debit/credit fields first (case-insensitive)
        row_lower = {k.lower(): v for k, v in row.items()}
        
        debit = None
        credit = None
        
        if 'debit' in row_lower and row_lower['debit']:
            debit = self._parse_decimal(row_lower['debit'])
        if 'credit' in row_lower and row_lower['credit']:
            credit = self._parse_decimal(row_lower['credit'])
        
        if debit is not None:
            return -abs(debit)
        if credit is not None:
            return abs(credit)
        
        # Try single amount field (case-insensitive)
        # When there's a single Amount field, preserve the sign as-is
        # (CSV format already encodes: positive = credit, negative = debit)
        amount_fields = ['Amount', 'Transaction Amount']
        for field in amount_fields:
            amount_str = self._find_field_case_insensitive(row, [field])
            if amount_str:
                amount = self._parse_decimal(amount_str)
                if amount is not None:
                    # Preserve the sign - CSV already has correct encoding
                    return amount
        
        # Try explicit debit/credit amount fields
        debit_amount = self._find_field_case_insensitive(row, ['Amount Debit'])
        credit_amount = self._find_field_case_insensitive(row, ['Amount Credit'])
        
        if debit_amount:
            debit = self._parse_decimal(debit_amount)
            if debit is not None:
                return -abs(debit)
        if credit_amount:
            credit = self._parse_decimal(credit_amount)
            if credit is not None:
                return abs(credit)
        
        return None
    
    def _parse_balance(self, row: Dict[str, str]) -> Optional[Decimal]:
        """Standard Bank balance field"""
        balance_fields = ['Balance', 'Running Balance']
        
        for field in balance_fields:
            if field in row and row[field]:
                return self._parse_decimal(row[field])
        
        return None


def get_parser(bank_name: str) -> BankParser:
    """Get the appropriate parser for a bank name"""
    bank_name_upper = bank_name.upper().strip()
    
    if 'FNB' in bank_name_upper or 'FIRST NATIONAL BANK' in bank_name_upper:
        return FNBParser()
    elif 'ABSA' in bank_name_upper:
        return ABSAParser()
    elif 'STANDARD' in bank_name_upper or 'STD BANK' in bank_name_upper:
        return StandardBankParser()
    else:
        raise ValueError(f"Bank format not supported: {bank_name}")


def parse_csv_file(
    file_content: bytes,
    bank_name: str,
    delimiter: Optional[str] = None
) -> Tuple[List[BankParseResult], List[BankParseResult]]:
    """
    Parse a CSV file and return valid and error rows.
    
    Args:
        file_content: Raw CSV file bytes
        bank_name: Name of the bank (e.g., "FNB", "ABSA")
        delimiter: CSV delimiter (None = auto-detect)
    
    Returns:
        Tuple of (valid_results, error_results)
    """
    # Get parser
    parser = get_parser(bank_name)
    
    # Decode file
    try:
        content = file_content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            content = file_content.decode('latin-1')
        except UnicodeDecodeError:
            raise ValueError("Unable to decode file. Expected UTF-8 or Latin-1 encoding.")
    
    # Auto-detect delimiter if not provided
    if delimiter is None:
        sniffer = csv.Sniffer()
        sample = content[:1024]
        try:
            delimiter = sniffer.sniff(sample).delimiter
        except:
            delimiter = ','  # Default to comma
    
    # Parse CSV
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    
    valid_results = []
    error_results = []
    
    for row_number, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
        # Store row number in raw_data for reference
        row['_row_number'] = row_number
        result = parser.parse_row(row, row_number)
        
        if result.error:
            error_results.append(result)
        else:
            valid_results.append(result)
    
    return valid_results, error_results

