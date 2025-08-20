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
# Trading Account detection guard
# --------------------------------
BANNER = re.compile(r"MANAGEMENT REPORTS\s*-\s*TRADING ACCOUNT", re.I)

# Many STK261 layouts show a vertically stacked block like:
#   OPENING STOCK         R xxx
#   PURCHASES             R yyy
#   CLOSING STOCK         R zzz
#   COST OF SALES         R kkk
#
# Values can appear on the same line or after some spacing. We’ll capture the
# first money token on the same line as the label.

LABEL_PATTERNS = {
    "opening_stock": re.compile(r"\bOPENING\s+STOCK\b", re.I),
    "purchases":     re.compile(r"\bPURCHASES\b", re.I),
    "closing_stock": re.compile(r"\bCLOSING\s+STOCK\b", re.I),
    "cost_of_sales": re.compile(r"\bCOST\s+OF\s+SALES\b", re.I),
}

MONEY_TOKEN = re.compile(r"(-?\(?R?[\s\d,]*\.?\d+\)?)")

def _extract_value_from_line(line: str) -> Optional[float]:
    m = MONEY_TOKEN.search(line)
    return parse_money_any(m.group(1)) if m else None

def extract_trading_fields(text: str) -> Dict[str, Optional[float]]:
    fields = {
        "opening_stock": None,
        "purchases": None,
        "closing_stock": None,
        "cost_of_sales": None,
    }
    # Look line-by-line for labels and read the first money token on the line
    for raw in text.splitlines():
        line = raw.strip()
        for key, pat in LABEL_PATTERNS.items():
            if pat.search(line):
                val = _extract_value_from_line(line)
                # Keep first seen value (avoid overwriting if label appears in a header or summary)
                if fields[key] is None and val is not None:
                    fields[key] = val
    return fields

def parse_trading_account(pdf_path: Path) -> Dict[str, Any]:
    text = read_text(pdf_path)

    report_type_ok = bool(BANNER.search(text))

    pharmacy_id, pharmacy_name = detect_pharmacy(text)
    date_from, date_to = extract_date_range(text)

    fields = extract_trading_fields(text)

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
        print("Usage: python -m src.parsers.trading_account <file_or_dir_or_glob> [...]")
        sys.exit(1)

    targets: List[str] = []
    for arg in sys.argv[1:]:
        targets.extend(_expand_arg(arg))

    if not targets:
        print("No files found.")
        sys.exit(2)

    for t in targets:
        rec = parse_trading_account(Path(t))
        print(json.dumps(rec, ensure_ascii=False))
