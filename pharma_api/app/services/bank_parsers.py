"""
Bank CSV Parsers
Parses CSV files from different South African banks into standardized format.
"""

import csv
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation


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
    def _parse_date_string(date_str: str, formats: List[str]) -> Optional[str]:
        """Try parsing date string with multiple formats"""
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None


class FNBParser(BankParser):
    """Parser for FNB bank CSV format"""
    
    def _parse_date(self, row: Dict[str, str]) -> Optional[str]:
        """FNB typically uses formats like: 2025-03-15 or 15/03/2025"""
        date_fields = ['Date', 'Transaction Date', 'Value Date']
        
        for field in date_fields:
            if field in row and row[field]:
                date_str = row[field].strip()
                # Try common formats
                formats = [
                    '%Y-%m-%d',
                    '%d/%m/%Y',
                    '%d-%m-%Y',
                    '%Y/%m/%d',
                    '%d %b %Y',
                    '%d %B %Y'
                ]
                parsed = self._parse_date_string(date_str, formats)
                if parsed:
                    return parsed
        
        return None
    
    def _get_description(self, row: Dict[str, str]) -> Optional[str]:
        """FNB description fields"""
        desc_fields = ['Description', 'Transaction Description', 'Narrative', 'Details']
        
        for field in desc_fields:
            if field in row and row[field]:
                return row[field]
        
        return None
    
    def _parse_reference(self, row: Dict[str, str]) -> Optional[str]:
        """FNB reference fields"""
        ref_fields = ['Reference', 'Reference Number', 'Narrative', 'Contra']
        
        for field in ref_fields:
            if field in row and row[field]:
                return row[field].strip()
        
        return None
    
    def _parse_amount(self, row: Dict[str, str]) -> Optional[Decimal]:
        """FNB amount fields - positive for credits, negative for debits"""
        amount_fields = ['Amount', 'Transaction Amount', 'Debit', 'Credit']
        
        # Try debit/credit fields first
        debit = None
        credit = None
        
        if 'Debit' in row and row['Debit']:
            debit = self._parse_decimal(row['Debit'])
        if 'Credit' in row and row['Credit']:
            credit = self._parse_decimal(row['Credit'])
        
        if debit is not None:
            return -abs(debit)  # Negative for debits
        if credit is not None:
            return abs(credit)  # Positive for credits
        
        # Try single amount field
        for field in amount_fields:
            if field in row and row[field]:
                amount = self._parse_decimal(row[field])
                if amount is not None:
                    # If amount is already negative, keep it; otherwise assume it's a debit
                    return amount if amount < 0 else -abs(amount)
        
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
        date_fields = ['Date', 'Transaction Date', 'Posting Date', 'Value Date']
        
        for field in date_fields:
            if field in row and row[field]:
                date_str = row[field].strip()
                formats = [
                    '%Y-%m-%d',
                    '%d/%m/%Y',
                    '%d-%m-%Y',
                    '%Y/%m/%d',
                    '%d %b %Y',
                    '%d %B %Y'
                ]
                parsed = self._parse_date_string(date_str, formats)
                if parsed:
                    return parsed
        
        return None
    
    def _get_description(self, row: Dict[str, str]) -> Optional[str]:
        """ABSA description fields"""
        desc_fields = ['Description', 'Transaction Description', 'Narrative', 'Details', 'Memo']
        
        for field in desc_fields:
            if field in row and row[field]:
                return row[field]
        
        return None
    
    def _parse_reference(self, row: Dict[str, str]) -> Optional[str]:
        """ABSA reference fields"""
        ref_fields = ['Reference', 'Reference Number', 'Narrative', 'Contra', 'Cheque Number']
        
        for field in ref_fields:
            if field in row and row[field]:
                return row[field].strip()
        
        return None
    
    def _parse_amount(self, row: Dict[str, str]) -> Optional[Decimal]:
        """ABSA amount fields"""
        amount_fields = ['Amount', 'Transaction Amount', 'Debit', 'Credit', 'Withdrawal', 'Deposit']
        
        # Try debit/credit fields first
        debit = None
        credit = None
        
        if 'Debit' in row and row['Debit']:
            debit = self._parse_decimal(row['Debit'])
        if 'Credit' in row and row['Credit']:
            credit = self._parse_decimal(row['Credit'])
        if 'Withdrawal' in row and row['Withdrawal']:
            debit = self._parse_decimal(row['Withdrawal'])
        if 'Deposit' in row and row['Deposit']:
            credit = self._parse_decimal(row['Deposit'])
        
        if debit is not None:
            return -abs(debit)
        if credit is not None:
            return abs(credit)
        
        # Try single amount field
        for field in amount_fields:
            if field in row and row[field]:
                amount = self._parse_decimal(row[field])
                if amount is not None:
                    return amount if amount < 0 else -abs(amount)
        
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
        date_fields = ['Date', 'Transaction Date', 'Posting Date']
        
        for field in date_fields:
            if field in row and row[field]:
                date_str = row[field].strip()
                formats = [
                    '%Y-%m-%d',
                    '%d/%m/%Y',
                    '%d-%m-%Y',
                    '%Y/%m/%d'
                ]
                parsed = self._parse_date_string(date_str, formats)
                if parsed:
                    return parsed
        
        return None
    
    def _get_description(self, row: Dict[str, str]) -> Optional[str]:
        """Standard Bank description fields"""
        desc_fields = ['Description', 'Transaction Description', 'Narrative', 'Details']
        
        for field in desc_fields:
            if field in row and row[field]:
                return row[field]
        
        return None
    
    def _parse_reference(self, row: Dict[str, str]) -> Optional[str]:
        """Standard Bank reference fields"""
        ref_fields = ['Reference', 'Reference Number', 'Narrative']
        
        for field in ref_fields:
            if field in row and row[field]:
                return row[field].strip()
        
        return None
    
    def _parse_amount(self, row: Dict[str, str]) -> Optional[Decimal]:
        """Standard Bank amount fields"""
        amount_fields = ['Amount', 'Transaction Amount', 'Debit', 'Credit']
        
        debit = None
        credit = None
        
        if 'Debit' in row and row['Debit']:
            debit = self._parse_decimal(row['Debit'])
        if 'Credit' in row and row['Credit']:
            credit = self._parse_decimal(row['Credit'])
        
        if debit is not None:
            return -abs(debit)
        if credit is not None:
            return abs(credit)
        
        for field in amount_fields:
            if field in row and row[field]:
                amount = self._parse_decimal(row[field])
                if amount is not None:
                    return amount if amount < 0 else -abs(amount)
        
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

