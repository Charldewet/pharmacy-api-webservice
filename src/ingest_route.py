import sys
import glob
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .types import ReportType
from .classify import classify_file

# Import the parsers we have implemented
from .parsers.turnover import parse_turnover_summary
from .parsers.trading_account import parse_trading_account
from .parsers.scripts import parse_scripts
from .parsers.gp_report import parse_gp_report



# Optional: when we add parsers, import and map them here
# from .parsers.scripts import parse_scripts   # (PHM080) TODO
# from .parsers.gp_report import parse_gp_report  # (STK260) TODO


def _expand_arg(arg: str) -> List[str]:
    """
    Accept files, folders (recursive), or globs.
    """
    p = Path(arg)
    if p.is_dir():
        return [str(x) for x in p.rglob("*.pdf")]
    matches = glob.glob(arg)
    return matches if matches else [arg]


def _route_parse(path: str) -> Dict[str, Any]:
    """
    Classify the PDF, choose a parser (if available), and return a JSON-able dict.
    If unsupported type, return a minimal payload with status.
    """
    c = classify_file(Path(path))

    payload: Dict[str, Any] = {
        "path": c.path,
        "report_type": c.report_type,
        "pharmacy_id": c.pharmacy_id,
        "pharmacy_name": c.pharmacy_name,
        "date_from": getattr(c, "date_from", None),
        "date_to": getattr(c, "date_to", None),
    }

    if c.report_type is None:
        payload["status"] = "skipped_unclassified"
        payload["reason"] = "could_not_detect_report_type"
        return payload

    rtype = ReportType(c.report_type)

    # Dispatch to implemented parsers
    if rtype == ReportType.TURNOVER_SUMMARY:
        rec = parse_turnover_summary(Path(path))
        rec["status"] = "parsed"
        rec["report_type"] = c.report_type
        return rec

    if rtype == ReportType.TRADING_ACCOUNT:
        rec = parse_trading_account(Path(path))
        rec["status"] = "parsed"
        rec["report_type"] = c.report_type
        return rec
    
    if rtype == ReportType.DISPENSARY_SCRIPTS:
        rec = parse_scripts(Path(path))
        rec["status"] = "parsed"
        rec["report_type"] = c.report_type
        return rec
    
    if rtype == ReportType.GP_REPORT:
        rec = parse_gp_report(Path(path))
        rec["status"] = "parsed"
        rec["report_type"] = c.report_type
        return rec


    # Not implemented yet → return minimal info so receipts table can still be populated
    payload["status"] = "skipped_no_parser"
    payload["reason"] = f"no_parser_for_{c.report_type}"
    return payload


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Usage: python -m src.ingest_route <file_or_dir_or_glob> [...]",
              file=sys.stderr)
        return 1

    targets: List[str] = []
    for arg in argv[1:]:
        targets.extend(_expand_arg(arg))

    if not targets:
        print("No files found.", file=sys.stderr)
        return 2

    # Stream JSON Lines to stdout (one JSON object per input PDF)
    for t in targets:
        try:
            rec = _route_parse(t)
        except Exception as e:
            # Never crash the whole batch; emit a structured error record
            rec = {
                "path": t,
                "status": "error",
                "error": str(e),
            }
        print(json.dumps(rec, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
