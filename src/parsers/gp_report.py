import re
import sys
import glob
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime

from pdfminer.high_level import extract_text

# --------------------------------
# Helpers & small utils
# --------------------------------
try:
    from ..types import PharmacyId
except Exception:
    from enum import Enum
    class PharmacyId(int, Enum):
        REITZ = 1
        WINTERTON = 2


def read_text(pdf_path: Path) -> str:
    """Return full PDF text (preserve case for description fidelity)."""
    return extract_text(str(pdf_path)) or ""


def parse_number(s: str) -> Optional[float]:
    """Parse numeric token like '1,234.56' or '(123.45)' or '-12.3' → float."""
    if not s:
        return None
    s = s.strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    val = float(m.group(0))
    return -val if (neg or s.startswith("-")) else val


# Pharmacy detection (robust to truncation of WINTERTON as WINTERTO)
PHARMACY_PATTERNS = (
    (PharmacyId.REITZ,     "REITZ APTEEK",            r"\bREITZ\s+APTEEK\b"),
    (PharmacyId.WINTERTON, "TLC PHARMACY WINTERTON",  r"\bTLC\s+PHARMACY\s+WINTERTO(?:N)?\b"),
)

def detect_pharmacy(text_upper: str) -> Tuple[Optional[int], Optional[str]]:
    for pid, canonical, pat in PHARMACY_PATTERNS:
        if re.search(pat, text_upper, re.I):
            return int(pid), canonical
    return None, None


# Business date range extraction
DATE_PATTERNS = [
    r"DATE\s+RANGE\s*-\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    r"RANGE-\s*DATE\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    r"DATE\s+FROM\s*:\s*(\d{4}/\d{2}/\d{2})\s*DATE\s+TO\s*:\s*(\d{4}/\d{2}/\d{2})",
    r"\b(\d{4}/\d{2}/\d{2})\s*-\s*(\d{4}/\d{2}/\d{2})\s*\(INCLUSIVE\)",
]

def _iso(d: str) -> str:
    return datetime.strptime(d, "%Y/%m/%d").date().isoformat()

def extract_date_range(text_upper: str) -> Tuple[Optional[str], Optional[str]]:
    for pat in DATE_PATTERNS:
        m = re.search(pat, text_upper, re.I)
        if m:
            return _iso(m.group(1)), _iso(m.group(2))
    dates = re.findall(r"\b(\d{4}/\d{2}/\d{2})\b", text_upper)
    if len(dates) >= 2:
        return _iso(dates[0]), _iso(dates[1])
    return None, None


# --------------------------------
# Report detection guard
# --------------------------------
BANNER = re.compile(r"\bGROSS\s+PROFIT\s+REPORT\b", re.I)
COL_HEADERS = re.compile(r"\bSALES-VAL\b.*\bSALES-COST\b.*\bGROSS-PROF\b", re.I)

# --------------------------------
# Row parsing
# Expected start of a data row:
#   <DEPT_CODE> <PRODUCT_CODE> <DESCRIPTION ...> <NUMS ...>
#
# where:
#   DEPT_CODE    = PDST01 / PDWB01 / HVLD03 (pattern: 4 letters + 2 digits)
#   PRODUCT_CODE = LP9077033 (pattern: 2 letters + 6+ digits)
#
# We consider the numeric tail to be the last 5–7 numbers on the line:
#   [on_hand] [sales_qty] [sales_value] [cost_of_sales] [gross_profit] [turnover_pct] [gp_pct]
# If fewer than 7 numbers are present, left-pad with None to keep column order stable.
# --------------------------------
DEPT_RE = re.compile(r"\b([A-Z]{4}\d{2})\b")
PROD_RE = re.compile(r"\b([A-Z]{2}\d{6,})\b")
NUM_RE  = re.compile(r"-?\(?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?|-?\d+(?:\.\d+)?")


def parse_line(line: str) -> Optional[Dict[str, Any]]:
    # Skip obvious non-data lines
    if not line or len(line) < 8:
        return None
    up = line.upper()
    if (set(up) <= set("-_= ")) or ("GROSS PROFIT REPORT" in up) or ("SALES-VAL" in up and "SALES-COST" in up):
        return None
    if up.startswith("DEPARTMENT") or up.startswith("DEPT "):
        return None
    if "TOTAL" in up and ("DEPARTMENT" in up or "TURNOVER" in up):
        return None

    md = DEPT_RE.search(line)
    mp = PROD_RE.search(line)
    if not md or not mp:
        return None
    if mp.start() < md.start():
        # product code should come after department code in a data row
        return None

    dept_code = md.group(1)
    product_code = mp.group(1)

    # Tail after product code
    tail = line[mp.end():].strip()

    # Collect numeric tokens at the end of the line
    nums = NUM_RE.findall(tail)
    # We need at least sales_qty..gp_pct → 5 tokens minimum to be useful
    if len(nums) < 5:
        return None

    # The description is what's left after removing the trailing numeric tokens
    desc_part = tail
    for tok in reversed(nums):
        desc_part = re.sub(r"\s*" + re.escape(tok) + r"\s*$", "", desc_part, count=1)
    description = desc_part.strip(" -:\t")
    if not description:
        return None

    # Map trailing numbers from the RIGHT; keep only the last 7 max
    tokens = nums[-7:]
    values = [parse_number(t) for t in tokens]
    # Left-pad to 7 positions
    while len(values) < 7:
        values.insert(0, None)

    on_hand, sales_qty, sales_value, cost_of_sales, gross_profit, turnover_pct, gp_pct = values

    return {
        "dept_code": dept_code,
        "product_code": product_code,
        "description": description,
        "on_hand": on_hand,
        "sales_qty": sales_qty,
        "sales_value": sales_value,     # Report assumed excl. VAT
        "cost_of_sales": cost_of_sales,
        "gross_profit": gross_profit,
        "turnover_pct": turnover_pct,
        "gp_pct": gp_pct,
    }


def parse_gp_report(pdf_path: Path) -> Dict[str, Any]:
    text = read_text(pdf_path)
    text_upper = text.upper()

    report_type_ok = bool(BANNER.search(text_upper) and COL_HEADERS.search(text_upper))

    pharmacy_id, pharmacy_name = detect_pharmacy(text_upper)
    date_from, date_to = extract_date_range(text_upper)

    lines_out: List[Dict[str, Any]] = []

    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw.strip())
        rec = parse_line(line)
        if rec:
            rec.update({
                "pharmacy_id": pharmacy_id,
                "pharmacy_name": pharmacy_name,
                "date_from": date_from,
                "date_to": date_to,
                "path": str(pdf_path),
            })
            lines_out.append(rec)

    return {
        "path": str(pdf_path),
        "report_type_ok": report_type_ok,
        "pharmacy_id": pharmacy_id,
        "pharmacy_name": pharmacy_name,
        "date_from": date_from,
        "date_to": date_to,
        "line_count": len(lines_out),
        "lines": lines_out,
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
        print("Usage: python -m src.parsers.gp_report <file_or_dir_or_glob> [...]")
        sys.exit(1)

    targets: List[str] = []
    for arg in sys.argv[1:]:
        targets.extend(_expand_arg(arg))

    if not targets:
        print("No files found.")
        sys.exit(2)

    for t in targets:
        rec = parse_gp_report(Path(t))
        print(json.dumps(rec, ensure_ascii=False))
