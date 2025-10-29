import re
import sys
import glob
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Tuple, List

from pdfminer.high_level import extract_text
from .types import ReportType, PharmacyId


# ----------------------------
# Email Subject Classification
# ----------------------------
EMAIL_PHARMACY_PATTERNS: Tuple[Tuple[PharmacyId, str, str], ...] = (
    # (id, canonical_name, subject_pattern)
    (PharmacyId.REITZ,     "REITZ APTEEK",            r"REITZ\s+PHARMACY"),
    (PharmacyId.WINTERTON, "TLC PHARMACY WINTERTON",  r"TLC\s+WINTERTON\s+PHARMACY"),
    (PharmacyId.ROOS,      "ROOS PHARMACY",           r"ROOS\s+PHARMACY"),
    (PharmacyId.VILLIERS,  "TLC VILLIERS PHARMACY",   r"TLC\s+VILLIERS\s+PHARMACY"),
    (PharmacyId.TUGELA,    "TLC TUGELA PHARMACY",     r"TLC\s+TUGELA\s+PHARMACY"),
    (PharmacyId.UMDONI,    "TLC UMDONI",              r"TLC\s+UMDONI"),
)

def classify_email_subject(subject: str) -> Optional[Tuple[PharmacyId, str]]:
    """
    Classify pharmacy from email subject line.
    More reliable than PDF content parsing.
    """
    subject_upper = subject.upper()
    for pid, canonical, pat in EMAIL_PHARMACY_PATTERNS:
        if re.search(pat, subject_upper, re.I):
            return pid, canonical
    return None


# ----------------------------
# Fast PDF head reader
# ----------------------------
def read_head(pdf_path: Path, pages: int = 2, max_chars: int = 8000) -> str:
    """
    Extract text from just the first `pages` (default 2). This avoids parsing
    the whole document and is significantly faster. If the head comes back
    empty (rare), we fall back to full-document extraction.
    """
    try:
        head = extract_text(str(pdf_path), page_numbers=list(range(pages))) or ""
        if not head:
            # fallback for odd files where early pages are image-only
            head = extract_text(str(pdf_path)) or ""
    except Exception:
        # last-resort fallback
        head = extract_text(str(pdf_path)) or ""

    return head[:max_chars].upper()


# ----------------------------
# Report-type detection rules
# ----------------------------
PATTERNS: List[Tuple[ReportType, List[str]]] = [
    # Script Statistics (Dispensary/Scripts)
    (ReportType.DISPENSARY_SCRIPTS, [
        r"\bSCRIPT STATISTICS\b",
        r"\bTOTAL REVENUE\b",
    ]),
    # Finalizing / Turnover Summary
    (ReportType.TURNOVER_SUMMARY, [
        r"FINALIZING REPORT\s*\(TURNOVER SUMMARY\)",
        r"\bTOTAL TURNOVER\b",
    ]),
    # Trading Account (Management)
    (ReportType.TRADING_ACCOUNT, [
        r"MANAGEMENT REPORTS\s*-\s*TRADING ACCOUNT",
        r"\bOPENING STOCK\b.*\bCLOSING STOCK\b.*\bCOST OF SALES\b",
    ]),
    # Gross Profit (per product/department)
    (ReportType.GP_REPORT, [
        r"\bGROSS PROFIT REPORT\b",
        r"\bSALES-VAL\b.*\bSALES-COST\b.*\bGROSS-PROF\b",
    ]),
]

def classify_text(text_head: str) -> Optional[ReportType]:
    for rtype, rules in PATTERNS:
        if all(re.search(p, text_head, re.I | re.S) for p in rules):
            return rtype
    # Conservative fallbacks
    if "SCRIPT STATISTICS" in text_head and "TOTAL REVENUE" in text_head:
        return ReportType.DISPENSARY_SCRIPTS

    return None


# ----------------------------
# Pharmacy detection
# (tolerant to line breaks / truncation like WINTERTO)
# ----------------------------
PHARMACY_PATTERNS: Tuple[Tuple[PharmacyId, str, str], ...] = (
    # (id, canonical_name, regex)
    (PharmacyId.REITZ,     "REITZ APTEEK",            r"\bREITZ\s+APTEEK\b"),
    (PharmacyId.WINTERTON, "TLC PHARMACY WINTERTON",  r"\bTLC\s+PHARMACY\s+WINTERTO(?:N)?\b"),
    (PharmacyId.ROOS,      "THE LOCAL CHOICE PHARMACY ROOS", r"\bTHE\s+LOCAL\s+CHOICE\s+PHARMACY\b"),
)

def detect_pharmacy(text_head: str) -> Optional[Tuple[PharmacyId, str]]:
    for pid, canonical, pat in PHARMACY_PATTERNS:
        if re.search(pat, text_head, re.I):
            return pid, canonical
    return None


# ----------------------------
# Date range extraction
# (business date printed in the header area, not the corner timestamp)
# ----------------------------
DATE_PATTERNS = [
    # STK261: "DATE RANGE - FROM: 2025/08/15 TO: 2025/08/15"
    r"DATE\s+RANGE\s*-\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    # INV249: "RANGE- DATE From:2025/08/15  TO:2025/08/15"
    r"RANGE-\s*DATE\s*FROM:\s*(\d{4}/\d{2}/\d{2})\s*TO:\s*(\d{4}/\d{2}/\d{2})",
    # INV014: "DATE FROM : 2025/08/15   DATE TO : 2025/08/15"
    r"DATE\s+FROM\s*:\s*(\d{4}/\d{2}/\d{2})\s*DATE\s+TO\s*:\s*(\d{4}/\d{2}/\d{2})",
    # PHM080: "2025/08/15 - 2025/08/15 (INCLUSIVE)"
    r"\b(\d{4}/\d{2}/\d{2})\s*-\s*(\d{4}/\d{2}/\d{2})\s*\(INCLUSIVE\)",
]

def _iso(dmyslash: str) -> str:
    # "YYYY/MM/DD" -> "YYYY-MM-DD"
    return datetime.strptime(dmyslash, "%Y/%m/%d").date().isoformat()

def extract_date_range(text_head: str) -> Tuple[Optional[str], Optional[str]]:
    # 1) Try specific patterns
    for pat in DATE_PATTERNS:
        m = re.search(pat, text_head, re.I)
        if m:
            return _iso(m.group(1)), _iso(m.group(2))
    # 2) Fallback: take first two YYYY/MM/DD tokens in the header blob
    dates = re.findall(r"\b(\d{4}/\d{2}/\d{2})\b", text_head)
    if len(dates) >= 2:
        return _iso(dates[0]), _iso(dates[1])
    return None, None


# ----------------------------
# Single-file classifier
# ----------------------------
def classify_file(pdf_path: Path) -> SimpleNamespace:
    head = read_head(pdf_path, pages=2)
    report_type = classify_text(head)
    pharm = detect_pharmacy(head)
    date_from, date_to = extract_date_range(head)

    return SimpleNamespace(
        path=str(pdf_path),
        report_type=report_type.value if report_type else None,
        pharmacy_id=(pharm[0].value if pharm else None),
        pharmacy_name=(pharm[1] if pharm else None),
        date_from=date_from,
        date_to=date_to,
    )


# ----------------------------
# CLI
# Supports: files, folders (recursive), and globs
# ----------------------------
def _expand_arg(arg: str) -> List[str]:
    p = Path(arg)
    if p.is_dir():
        return [str(x) for x in p.rglob("*.pdf")]
    matches = glob.glob(arg)
    return matches if matches else [arg]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.classify <file_or_dir_or_glob> [...]")
        sys.exit(1)

    targets: List[str] = []
    for arg in sys.argv[1:]:
        targets.extend(_expand_arg(arg))

    if not targets:
        print("No files found.")
        sys.exit(2)

    for t in targets:
        res = classify_file(Path(t))
        print(
            f"{res.path} -> type={res.report_type} | pharmacy_id={res.pharmacy_id} "
            f"| pharmacy_name={res.pharmacy_name} | from={res.date_from} | to={res.date_to}"
        )
