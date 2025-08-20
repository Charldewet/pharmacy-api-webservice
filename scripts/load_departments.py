import argparse
import csv
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.loader import upsert_department


def parse_args():
    p = argparse.ArgumentParser(description="Load department codes/names into pharma.departments")
    p.add_argument("csv_path", help="Path to Departments.csv")
    p.add_argument("--encoding", default="utf-8", help="CSV file encoding (default: utf-8)")
    p.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
    p.add_argument("--has-header", action="store_true", help="Set if the CSV has a header row")
    return p.parse_args()


essential_headers = {"Department Code", "Department Name"}


def iter_rows(csv_path: str, encoding: str, delimiter: str, has_header: bool):
    with open(csv_path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = None
        if has_header:
            header = next(reader, None)
            if not header or set(header) < essential_headers:
                raise ValueError(f"CSV header must include {essential_headers}, got: {header}")
        for row in reader:
            # Expect exactly two columns when no header, else map by header names
            if has_header:
                row_map = {header[i]: (row[i].strip() if i < len(row) else None) for i in range(len(header))}
                code = row_map.get("Department Code")
                name = row_map.get("Department Name")
            else:
                if len(row) < 2:
                    # skip incomplete rows
                    continue
                code = row[0].strip()
                name = row[1].strip() if len(row) > 1 else None
            if not code:
                continue
            yield code, (name or None)


def main():
    args = parse_args()
    loaded = 0
    for code, name in iter_rows(args.csv_path, args.encoding, args.delimiter, args.has_header):
        upsert_department(code, name)
        loaded += 1
    print(f"Processed {loaded} rows from {args.csv_path}")


if __name__ == "__main__":
    sys.exit(main()) 