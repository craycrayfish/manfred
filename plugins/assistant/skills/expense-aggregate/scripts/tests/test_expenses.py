import json
import sys
from pathlib import Path

import pytest

import classify
import expenses


AMAZON_TEXT = """
Final Details for Order #114-2938471-9384756
Order Placed: August 3, 2025
amazon.com order number: 114-2938471-9384756
Item(s) Subtotal: $52.10
Grand Total: $57.30
Visa | Last digits: 4321
"""


def test_extract_amazon(monkeypatch, tmp_path):
    pdf = tmp_path / "invoice.pdf"
    pdf.write_text("stub")
    monkeypatch.setattr(expenses, "pdf_text", lambda p: AMAZON_TEXT)
    row = expenses.extract_amazon(pdf)
    assert row["date"] == "2025-08-03"
    assert row["amount"] == "57.30"
    assert row["currency"] == "USD"
    assert row["vendor"] == "Amazon"
    assert row["confidence"] == "high"
    assert "114-2938471-9384756" in row["description"]


ORDER_SUMMARY_TEXT = """
Order Summary
Order placed April 21, 2026  Order # 114-6341501-8223413
Amazon Visa ending in 1551
Item(s) Subtotal: $10.99
Rewards Points: -$12.06
Grand Total: $0.00
Refund Total $10.85
Your package was left near the front door or porch.
2 HiLetgo BTS7960 43A High Power Motor Driver Module
for Arduino
Sold by: HiLetgo
Return complete
"""


def test_extract_amazon_order_summary_layout(monkeypatch, tmp_path):
    pdf = tmp_path / "o.pdf"
    pdf.write_text("stub")
    monkeypatch.setattr(expenses, "pdf_text", lambda p: ORDER_SUMMARY_TEXT)
    row = expenses.extract_amazon(pdf)
    assert row["date"] == "2026-04-21" and row["amount"] == "0.00"  # clamped, not -10.85
    assert row["confidence"] == "medium" and "[refunded -10.85]" in row["description"]
    assert row["payment_method"] == "Visa 1551"
    assert row["description"].startswith("HiLetgo BTS7960 43A High Power Motor Driver Module for Arduino")
    assert "#114-6341501-8223413" in row["description"] and "rewards points -12.06" in row["description"]


def test_extract_amazon_unparseable_is_low_confidence(monkeypatch, tmp_path):
    pdf = tmp_path / "junk.pdf"
    pdf.write_text("stub")
    monkeypatch.setattr(expenses, "pdf_text", lambda p: "nothing useful here")
    assert expenses.extract_amazon(pdf)["confidence"] == "low"


def _work(tmp_path, name="a.pdf", category="amazon"):
    src = tmp_path / "unprocessed" / category
    src.mkdir(parents=True)
    (tmp_path / "processed" / category).mkdir(parents=True)
    f = src / name
    f.write_text("receipt bytes")
    return f


def _append(tmp_path, rows, monkeypatch):
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(rows)))
    expenses.cmd_append(tmp_path, "2025-08-23")


def test_append_writes_row_moves_file_and_dedupes(tmp_path, monkeypatch, capsys):
    f = _work(tmp_path)
    row = {"date": "2025-08-03", "vendor": "Amazon", "amount": "57.30",
           "currency": "USD", "category": "office", "source_file": str(f)}

    _append(tmp_path, [row], monkeypatch)
    capsys.readouterr()

    csv_text = (tmp_path / "expenses.csv").read_text()
    assert csv_text.startswith(",".join(expenses.FIELDS))
    assert "57.30" in csv_text and "processed/amazon/a.pdf" in csv_text
    assert not f.exists() and (tmp_path / "processed" / "amazon" / "a.pdf").exists()

    # Re-appending the same (now moved) file is a no-op: hash already in the ledger.
    row["source_file"] = str(tmp_path / "processed" / "amazon" / "a.pdf")
    _append(tmp_path, [row], monkeypatch)
    out = json.loads(capsys.readouterr().out)
    assert out["written"] == [] and len(out["skipped_duplicates"]) == 1
    assert (tmp_path / "expenses.csv").read_text() == csv_text


def test_append_normalises_unknown_category(tmp_path, monkeypatch, capsys):
    f = _work(tmp_path, "b.jpg", "photos")
    _append(tmp_path, [{"amount": "9.00", "category": "Dining", "source_file": str(f)}], monkeypatch)
    capsys.readouterr()
    assert "uncategorized" in (tmp_path / "expenses.csv").read_text()


@pytest.mark.parametrize("name,expected", [("a.jpg", "photos"), ("b.heic", "photos"),
                                           ("c.png", "screenshots"), ("d.txt", "other")])
def test_classify_by_extension(tmp_path, name, expected):
    f = tmp_path / name
    f.write_bytes(b"x" * 32)
    assert classify.classify(f) == expected


def test_classify_amazon_pdf_by_filename(tmp_path):
    f = tmp_path / "amazon-invoice.pdf"
    f.write_bytes(b"%PDF-1.4 not really a pdf")
    assert classify.classify(f) == "amazon"


def test_plan_skips_already_filed_files(tmp_path):
    (tmp_path / "loose.jpg").write_bytes(b"x")
    filed = tmp_path / "unprocessed" / "photos"
    filed.mkdir(parents=True)
    (filed / "old.jpg").write_bytes(b"y")
    moves = classify.plan(tmp_path, tmp_path)
    assert [Path(m["src"]).name for m in moves] == ["loose.jpg"]
    assert moves[0]["dest"].endswith("unprocessed/photos/loose.jpg")


def test_plan_avoids_name_collisions(tmp_path):
    for d in ("one", "two"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "receipt.jpg").write_bytes(b"x")
    dests = [Path(m["dest"]).name for m in classify.plan(tmp_path, tmp_path)]
    assert sorted(dests) == ["receipt-1.jpg", "receipt.jpg"]


def test_append_never_clobbers_processed_file(tmp_path, monkeypatch, capsys):
    f = _work(tmp_path, "receipt.jpg", "photos")
    (tmp_path / "processed" / "photos" / "receipt.jpg").write_text("earlier receipt")
    _append(tmp_path, [{"amount": "5.00", "source_file": str(f)}], monkeypatch)
    out = json.loads(capsys.readouterr().out)
    assert out["errors"] == [] and len(out["written"]) == 1
    assert (tmp_path / "processed" / "photos" / "receipt.jpg").read_text() == "earlier receipt"
    assert len(list((tmp_path / "processed" / "photos").iterdir())) == 2


def test_append_rejects_bad_amount_and_leaves_file(tmp_path, monkeypatch, capsys):
    f = _work(tmp_path, "c.png", "screenshots")
    _append(tmp_path, [{"amount": "$12.50", "source_file": str(f)}], monkeypatch)
    out = json.loads(capsys.readouterr().out)
    assert out["written"] == [] and len(out["errors"]) == 1
    assert f.exists()
    assert "12.50" not in (tmp_path / "expenses.csv").read_text()
