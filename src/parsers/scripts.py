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
    txt = extract_text(str(pdf_path)) or ""
    return txt.upper()


def parse_money_any(s: str) -> Optional[float]:
    """Parse R-values like 'R 12,345.67', '(12,345.67)', '12345.67' → float."""
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


PHARMACY_PATTERNS = (
    (PharmacyId.REITZ,     "REITZ APTEEK",            r"\bREITZ\s+APTEEK\b"),
    (PharmacyId.WINTERTON, "TLC PHARMACY WINTERTON",  r"\bTLC\s+PHARMACY\s+WINTERTO(?:N)?\b"),
)

def detect_pharmacy(head: str) -> Tuple[Optional[int], Optional[str]]:
    for pid, canonical, pat in PHARMACY_PATTERNS:
        if re.search(pat, head, re.I):
            return int(pid), canonical
    return None, None


DATE_PATTERNS = [
    r"DATE\s+RANGE\s*-\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    r"RANGE-\s*DATE\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    r"DATE\s+FROM\s*:\s*(\d{4}/\d{2}/\d{2})\s*DATE\s+TO\s*:\s*(\d{4}/\d{2}/\d{2})",
    r"\b(\d{4}/\d{2}/\d{2})\s*-\s*(\d{4}/\d{2}/\d{2})\s*\(INCLUSIVE\)",
]

def _iso(d: str) -> str:
    return datetime.strptime(d, "%Y/%m/%d").date().isoformat()

def extract_date_range(head: str) -> Tuple[Optional[str], Optional[str]]:
    for pat in DATE_PATTERNS:
        m = re.search(pat, head, re.I)
        if m:
            return _iso(m.group(1)), _iso(m.group(2))
    dates = re.findall(r"\b(\d{4}/\d{2}/\d{2})\b", head)
    if len(dates) >= 2:
        return _iso(dates[0]), _iso(dates[1])
    return None, None


# --------------------------------
# Script Statistics detection guard
# --------------------------------
BANNER = re.compile(r"\bSCRIPT\s+STATISTICS\b", re.I)

# Totals patterns:
#   "TOTAL REVENUE .... R 12,345.67"  (this is VAT-incl; we will divide by 1.15)
PAT_TOTAL_REVENUE = re.compile(
    r"\bTOTAL\s+REVENUE\b[^\n\r]*?(-?\(?R?[\s\d,]*\.?\d+\)?)", re.I
)

# Original variants we looked for (may not appear in your layout):
PAT_SCRIPTS_QTY = re.compile(
    r"\b(?:TOTAL\s+SCRIPTS|TOTAL\s+RX|TOTAL\s+PRESCRIPTIONS|NO\.?\s+OF\s+SCRIPTS|NUMBER\s+OF\s+SCRIPTS)\b"
    r"[^\n\r]*?(-?[\d,]+)", re.I
)

# NEW: Your report line
#   "NUMBER OF DOCUMENTS - DISPENSED   : ... TOTAL <87>"
PAT_DOCS_DISPENSED_LINE = re.compile(
    r"\bNUMBER\s+OF\s+DOCUMENTS\s*[-–]\s*DISPENSED\b", re.I
)

INT_TOKEN = re.compile(r"-?[\d,]+")


def _last_int_in_line(line: str) -> Optional[int]:
    ints = [parse_int_any(x) for x in INT_TOKEN.findall(line)]
    ints = [i for i in ints if i is not None]
    return ints[-1] if ints else None


def extract_scripts_fields(text: str) -> Dict[str, Optional[float]]:
    # 1) Total Revenue (incl VAT) → convert to excl by /1.15
    dispensary_turnover_excl = None
    m = PAT_TOTAL_REVENUE.search(text)
    if m:
        incl = parse_money_any(m.group(1))
        if incl is not None:
            dispensary_turnover_excl = round(incl / 1.15, 2)

    # 2) Scripts quantity
    scripts_qty = None

    # 2a) Try simple variants first
    m = PAT_SCRIPTS_QTY.search(text)
    if m:
        scripts_qty = parse_int_any(m.group(1))

    # 2b) Fallback to "NUMBER OF DOCUMENTS - DISPENSED" → take the last integer on that line (TOTAL)
    if scripts_qty is None:
        for raw in text.splitlines():
            line = raw.strip()
            if PAT_DOCS_DISPENSED_LINE.search(line):
                scripts_qty = _last_int_in_line(line)
                if scripts_qty is not None:
                    break

    # 3) Avg script value (based on VAT-exclusive revenue)
    avg_script_value = None
    if dispensary_turnover_excl is not None and scripts_qty and scripts_qty > 0:
        avg_script_value = round(dispensary_turnover_excl / scripts_qty, 2)

    return {
        "dispensary_turnover": dispensary_turnover_excl,  # VAT-exclusive
        "scripts_qty": scripts_qty,
        "avg_script_value": avg_script_value,
    }


def parse_scripts(pdf_path: Path) -> Dict[str, Any]:
    text = read_text(pdf_path)

    report_type_ok = bool(BANNER.search(text))

    pharmacy_id, pharmacy_name = detect_pharmacy(text)
    date_from, date_to = extract_date_range(text)

    fields = extract_scripts_fields(text)

    return {
        "path": str(pdf_path),
        "report_type_ok": report_type_ok,
        "pharmacy_id": pharmacy_id,
        "pharmacy_name": pharmacy_name,
        "date_from": date_from,
        "date_to": date_to,
        **fields,
    }


# --------------------------------
# CLI
# --------------------------------
def _expand_arg(arg: str) -> List[str]:
    p = Path(arg)
    if p.is_dir():
        return [str(x) for x in p.rglob("*.pdf")]
    matches = glob.glob(arg)
    return matches if matches else [arg]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.parsers.scripts <file_or_dir_or_glob> [...]")
        sys.exit(1)

    targets: List[str] = []
    for arg in sys.argv[1:]:
        targets.extend(_expand_arg(arg))

    if not targets:
        print("No files found.")
        sys.exit(2)

    for t in targets:
        rec = parse_scripts(Path(t))
        print(json.dumps(rec, ensure_ascii=False))
