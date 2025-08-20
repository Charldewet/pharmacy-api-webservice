import re
import sys
import glob
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime

from pdfminer.high_level import extract_text

# --------------------------------
# Shared helpers (inline for now)
# --------------------------------
try:
    from ..types import PharmacyId
except Exception:
    from enum import Enum
    class PharmacyId(int, Enum):
        REITZ = 1
        WINTERTON = 2


def read_text(pdf_path: Path) -> str:
    """Read full text (uppercase) for robust matching."""
    txt = extract_text(str(pdf_path)) or ""
    return txt.upper()


def parse_money_any(s: str) -> Optional[float]:
    """Parse money strings like 'R 12,345.67', '(123.45)', '12345.67'."""
    if not s:
        return None
    s = s.strip()
    s = re.sub(r"[R\s]", "", s, flags=re.I)
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    m = re.search(r"-?[\d,]*\.?\d+", s)
    if not m:
        return None
    num = m.group(0).replace(",", "")
    try:
        val = float(num)
        return -val if neg or s.startswith("-") else val
    except ValueError:
        return None


def parse_int_any(s: str) -> Optional[int]:
    """Parse integers like '1,234' → 1234."""
    if not s:
        return None
    m = re.search(r"-?[\d,]+", s.strip())
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _iso(d: str) -> str:
    return datetime.strptime(d, "%Y/%m/%d").date().isoformat()


# ----------------------------
# Pharmacy detection (robust)
# ----------------------------
PHARMACY_PATTERNS = (
    (PharmacyId.REITZ,     "REITZ APTEEK",            r"\bREITZ\s+APTEEK\b"),
    (PharmacyId.WINTERTON, "TLC PHARMACY WINTERTON",  r"\bTLC\s+PHARMACY\s+WINTERTO(?:N)?\b"),
)
def detect_pharmacy(head: str) -> Tuple[Optional[int], Optional[str]]:
    for pid, canonical, pat in PHARMACY_PATTERNS:
        if re.search(pat, head, re.I):
            return int(pid), canonical
    return None, None


# ----------------------------
# Business date range extraction
# ----------------------------
DATE_PATTERNS = [
    r"DATE\s+RANGE\s*-\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    r"RANGE-\s*DATE\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    r"DATE\s+FROM\s*:\s*(\d{4}/\d{2}/\d{2})\s*DATE\s+TO\s*:\s*(\d{4}/\d{2}/\d{2})",
    r"\b(\d{4}/\d{2}/\d{2})\s*-\s*(\d{4}/\d{2}/\d{2})\s*\(INCLUSIVE\)",
]
def extract_date_range(head: str) -> Tuple[Optional[str], Optional[str]]:
    for pat in DATE_PATTERNS:
        m = re.search(pat, head, re.I)
        if m:
            return _iso(m.group(1)), _iso(m.group(2))
    dates = re.findall(r"\b(\d{4}/\d{2}/\d{2})\b", head)
    if len(dates) >= 2:
        return _iso(dates[0]), _iso(dates[1])
    return None, None


# ----------------------------
# Report type guard (Turnover Summary / INV249)
# ----------------------------
TURNOVER_BANNER = re.compile(r"FINALIZING REPORT\s*\(TURNOVER SUMMARY\)", re.I)
TOTAL_TURNOVER_LABEL = re.compile(r"\bTOTAL\s+TURNOVER\b", re.I)

# ----------------------------
# Field extraction patterns (money)
# We pick Nett Excl for each totals row (3rd number on that line).
# ----------------------------
NUM_TOKEN = r"-?\(?R?[\s\d,]*\.?\d+\)?"
NUM = re.compile(NUM_TOKEN)

def _nums_in_line(line: str) -> List[float]:
    vals = []
    for tok in NUM.findall(line):
        v = parse_money_any(tok)
        if v is not None:
            vals.append(v)
    return vals

def extract_nett_excl_after_label(text: str, label_regex: str) -> Optional[float]:
    pat = re.compile(label_regex, re.I)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if pat.search(line):
            nums = _nums_in_line(line)
            if len(nums) >= 3:
                return nums[2]  # Nett Excl
    return None

LABEL_CASH_TOTALS     = r"\*\*\s*CASH\s+TOTALS"
LABEL_ACCOUNTS_TOTALS = r"\*\*\s*STANDARD\s+ACCOUNTS"
LABEL_COD_TOTALS      = r"\*\*\s*C\.?\s*O\.?\s*D\.?\s+TOTALS"
LABEL_TYPE_R_TOTALS   = r"\*\*\s*[\'’]R[\'’]\s+TOTALS"

TURNOVER_SUMMARY_LINE = re.compile(
    r"TURNOVER\s+SUMMARY.*?=\s*(" + NUM_TOKEN + r")\s+NETT\s*\(EXCLUSIVE\)",
    re.I | re.S
)

def extract_turnover_nett_excl(text: str) -> Optional[float]:
    m = TURNOVER_SUMMARY_LINE.search(text)
    if m:
        return parse_money_any(m.group(1))
    # Fallback: TOTAL TURNOVER row → take the 3rd number
    for raw in text.splitlines():
        line = raw.strip()
        if re.search(r"\*\*\s*TOTAL\s+TURNOVER\b", line, re.I):
            nums = _nums_in_line(line)
            if len(nums) >= 3:
                return nums[2]
    return None


# ----------------------------
# NEW: Count extraction (Invoices + Scripts for Cash/Account only)
# We ignore Refunds, and ignore Type 'R' entirely.
# Strategy: for a line containing "INVOICES" or "SCRIPTS", the penultimate
# numeric token on the line is the Count; the last numeric is the Average.
# (Matches your sample layout.) :contentReference[oaicite:1]{index=1}
# ----------------------------
COUNTABLE_ROWS = re.compile(r"\b(INVOICES|SCRIPTS)\b", re.I)
SECTION_CASH   = re.compile(r"^\s*CASH-SALES\s*$", re.I)
SECTION_ACCT   = re.compile(r"^\s*ACCOUNT\s+SALES\s*$", re.I)
SECTION_TYPE_R = re.compile(r"^\s*TYPE\s*[\'’]R[\'’]\s+SALES\s*$", re.I)

def _penultimate_number_as_int(line: str) -> Optional[int]:
    nums = re.findall(r"-?[\d,]*\.?\d+", line)
    if len(nums) < 2:
        return None
    return parse_int_any(nums[-2])

def extract_transaction_count(text: str) -> int:
    current = None
    total = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Section tracking
        if SECTION_CASH.match(line):
            current = "CASH"
            continue
        if SECTION_ACCT.match(line):
            current = "ACCT"
            continue
        if SECTION_TYPE_R.match(line):
            current = "TYPE_R"
            continue

        # Only count within CASH or ACCT sections
        if current in ("CASH", "ACCT"):
            up = line.upper()
            # skip refund lines explicitly
            if "REFUND" in up:
                continue
            if COUNTABLE_ROWS.search(line):
                cnt = _penultimate_number_as_int(line)
                if isinstance(cnt, int) and cnt > 0:
                    total += cnt

        # In TYPE_R section we ignore all counts
    return total


# ----------------------------
# Core parse function
# ----------------------------
def parse_turnover_summary(pdf_path: Path) -> Dict[str, Any]:
    """
    Parse a Turnover Summary (INV249) PDF and return structured fields.
    """
    head = read_text(pdf_path)

    report_type_ok = bool(TURNOVER_BANNER.search(head) and TOTAL_TURNOVER_LABEL.search(head))

    pharmacy_id, pharmacy_name = detect_pharmacy(head)
    date_from, date_to = extract_date_range(head)

    # Money fields (Nett Excl)
    turnover      = extract_turnover_nett_excl(head)
    sales_cash    = extract_nett_excl_after_label(head, LABEL_CASH_TOTALS)
    sales_account = extract_nett_excl_after_label(head, LABEL_ACCOUNTS_TOTALS)
    sales_cod     = extract_nett_excl_after_label(head, LABEL_COD_TOTALS)  # may be None if not present that day
    type_r_sales  = extract_nett_excl_after_label(head, LABEL_TYPE_R_TOTALS)

    # NEW: transaction_count (Cash Invoices + Cash Scripts + Account Invoices + Account Scripts; exclude refunds & Type 'R')
    transaction_count = extract_transaction_count(head)

    # NEW: avg_basket = (turnover - type_r_sales) / transaction_count
    retail_excl_type_r = None
    if turnover is not None:
        retail_excl_type_r = turnover - (type_r_sales or 0.0)

    avg_basket = None
    if retail_excl_type_r is not None and transaction_count and transaction_count > 0:
        avg_basket = round(retail_excl_type_r / transaction_count, 2)

    return {
        "path": str(pdf_path),
        "report_type_ok": report_type_ok,
        "pharmacy_id": pharmacy_id,
        "pharmacy_name": pharmacy_name,
        "date_from": date_from,
        "date_to": date_to,
        "turnover": turnover,
        "sales_cash": sales_cash,
        "sales_account": sales_account,
        "sales_cod": sales_cod,
        "type_r_sales": type_r_sales,
        "transaction_count": transaction_count,
        "avg_basket": avg_basket,
    }


# ----------------------------
# CLI
# ----------------------------
def _expand_arg(arg: str) -> List[str]:
    p = Path(arg)
    if p.is_dir():
        return [str(x) for x in p.rglob("*.pdf")]
    matches = glob.glob(arg)
    return matches if matches else [arg]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.parsers.turnover <file_or_dir_or_glob> [...]")
        sys.exit(1)

    targets: List[str] = []
    for arg in sys.argv[1:]:
        targets.extend(_expand_arg(arg))

    if not targets:
        print("No files found.")
        sys.exit(2)

    for t in targets:
        rec = parse_turnover_summary(Path(t))
        print(json.dumps(rec, ensure_ascii=False))
