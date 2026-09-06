#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pypdf>=5.0"]
# ///
"""Expense extraction + ledger.

  expenses.py amazon <file.pdf>       -> one JSON row on stdout
  expenses.py append --workdir D      -> read JSON rows on stdin, dedupe, write CSV, file originals
  expenses.py pending --workdir D     -> list unprocessed files not yet in the ledger
"""

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

FIELDS = [
    "date", "vendor", "description", "amount", "currency",
    "category", "payment_method", "source_file", "confidence",
]
CATEGORIES = [
    "meals", "travel", "transport", "lodging", "software", "hardware",
    "office", "marketing", "professional_services", "utilities",
    "subscriptions", "other", "uncategorized",
]
LEDGER = ".expense-ledger.json"
CSV_NAME = "expenses.csv"

MONEY = r"[\$£€]?\s*([\d,]+\.\d{2})"
STATUS_LINE = re.compile(r"^(Your package|Package was|It was handed|Delivered|Arriving|Picked up|Return|FSA or HSA|Shipped|Out for delivery|Not yet shipped|Refund|\$[\d.,]+$)", re.I)
AMOUNT_OK = re.compile(r"\d+(\.\d{1,2})?")  # bare number; "" allowed for unreadable receipts


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(path)).pages)


def parse_date(s: str) -> str:
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def extract_amazon(path: Path) -> dict:
    """Amazon invoices have a stable layout, so regex beats a model here."""
    text = pdf_text(path)
    row = {f: "" for f in FIELDS}
    row.update(vendor="Amazon", category="uncategorized", currency="USD",
               source_file=str(path.resolve()), confidence="high")

    m = re.search(r"Order (?:Placed|Date)\s*:?\s*([A-Za-z0-9,/ ]+\d{4})", text, re.I)
    if m:
        row["date"] = parse_date(m.group(1))

    m = re.search(r"Order\s*(?:#|number)\s*:?\s*([\d-]{15,25})", text, re.I)
    order = m.group(1) if m else ""

    # First item title sits between the totals block and the first "Sold by:",
    # after zero or more delivery-status lines.
    m = re.search(r"Grand Total:[^\n]*\n(.+?)\nSold by:", text, re.S)
    lines = [ln for ln in (m.group(1).split("\n") if m else []) if not STATUS_LINE.match(ln)]
    item = re.sub(r"^\d{1,2} (?=[A-Z])", "", " ".join(lines)).strip()[:80]
    n_items = len(re.findall(r"^Sold by:", text, re.M))
    desc = item or f"Amazon order {order}"
    if n_items > 1:
        desc += f" (+{n_items - 1} more)"
    if order and item:
        desc += f" #{order}"

    m = re.search(rf"(?:Grand Total|Order Total)\s*:?\s*{MONEY}", text, re.I)
    if m:
        row["amount"] = m.group(1).replace(",", "")
    # Amazon prints "Refund Total $X" once any item in the order is refunded; charge = total - refund.
    m = re.search(rf"Refund Total\s*:?\s*{MONEY}", text, re.I)
    if m and row["amount"]:
        refund = float(m.group(1).replace(",", ""))
        row["amount"] = f"{max(0.0, float(row['amount']) - refund):.2f}"
        desc += f" [refunded -{refund:.2f}]"
    returns = re.findall(r"^(Return started|Return complete|Refund issued|Cancelled)$", text, re.M | re.I)
    if returns:
        desc += " [" + ", ".join(r.lower() for r in returns) + "]"
        row["confidence"] = "medium"
    credits = re.findall(rf"(Rewards Points|Gift Card Amount|Promotion Applied)\s*:?\s*-{MONEY}", text, re.I)
    if credits:
        desc += " [" + ", ".join(f"{k.lower()} -{v}" for k, v in credits) + "]"
    row["description"] = desc
    if "£" in text:
        row["currency"] = "GBP"
    elif "€" in text:
        row["currency"] = "EUR"

    m = re.search(r"(Visa|Mastercard|American Express|Amex|Discover)[^\d\n]{0,20}(\d{4})", text, re.I)
    if m:
        row["payment_method"] = f"{m.group(1)} {m.group(2)}"

    if not (row["date"] and row["amount"]):
        row["confidence"] = "low"
    return row


def load_ledger(workdir: Path) -> dict:
    p = workdir / LEDGER
    return json.loads(p.read_text()) if p.exists() else {}


def cmd_pending(workdir: Path) -> int:
    ledger = load_ledger(workdir)
    out = []
    for f in sorted((workdir / "unprocessed").rglob("*")):
        if f.is_file() and not f.name.startswith("."):
            if sha256(f) in ledger:
                out.append({"file": str(f), "category": f.parent.name, "already_processed": True})
            else:
                out.append({"file": str(f), "category": f.parent.name, "already_processed": False})
    print(json.dumps(out, indent=2))
    return 0


def cmd_append(workdir: Path, today: str) -> int:
    rows = json.load(sys.stdin)
    if isinstance(rows, dict):
        rows = [rows]
    ledger = load_ledger(workdir)
    csv_path = workdir / CSV_NAME
    written, skipped, errors = [], [], []

    try:
        with csv_path.open("a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            if csv_path.stat().st_size == 0:
                w.writeheader()
            for row in rows:
                src = Path(str(row.get("source_file") or ""))
                amount = str(row.get("amount") or "")
                if not src.is_file():
                    errors.append(f"missing source_file: {src}")
                    continue
                if amount and not AMOUNT_OK.fullmatch(amount):
                    errors.append(f"bad amount {amount!r} for {src.name}; want digits and one dot")
                    continue
                digest = sha256(src)
                if digest in ledger:
                    skipped.append(str(src))
                    continue
                if row.get("category") not in CATEGORIES:
                    row["category"] = "uncategorized"
                dest = workdir / "processed" / src.parent.name / src.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():  # never clobber an already-processed receipt
                    dest = dest.with_name(f"{dest.stem}-{digest[:8]}{dest.suffix}")
                try:
                    shutil.move(str(src), dest)  # move first: a failed move must not leave a CSV row behind
                except OSError as e:
                    errors.append(f"could not move {src}: {e}")
                    continue
                row["source_file"] = str(dest.relative_to(workdir))
                w.writerow({f: row.get(f) or "" for f in FIELDS})
                ledger[digest] = {"source_file": row["source_file"], "processed_at": today}
                written.append(row["source_file"])
    finally:
        # ponytail: ledger written once, not per row; a hard kill mid-batch orphans moved files in processed/
        (workdir / LEDGER).write_text(json.dumps(ledger, indent=2))
    print(json.dumps({"written": written, "skipped_duplicates": skipped, "errors": errors}, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("amazon")
    a.add_argument("file", type=Path)
    for name in ("append", "pending"):
        p = sub.add_parser(name)
        p.add_argument("--workdir", type=Path, required=True)
    args = ap.parse_args()

    if args.cmd == "amazon":
        print(json.dumps(extract_amazon(args.file), indent=2))
        return 0
    if args.cmd == "pending":
        return cmd_pending(args.workdir.resolve())
    return cmd_append(args.workdir.resolve(), date.today().isoformat())


if __name__ == "__main__":
    raise SystemExit(main())
