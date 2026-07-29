"""UTF-8 CSV and accessible Excel exports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from web_scraper.models import COLUMNS, PersonRecord


def _frame(records: list[PersonRecord]) -> pd.DataFrame:
    return pd.DataFrame([record.as_dict() for record in records], columns=COLUMNS)


def export_records(records: list[PersonRecord], output: str | Path) -> Path:
    """Export based on extension. Excel includes filters, frozen headers, and widths."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = _frame(records)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(path, index=False, encoding="utf-8")
    elif suffix in {".xlsx", ".xlsm"}:
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name="Scraped data")
            worksheet = writer.book["Scraped data"]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            header_fill = PatternFill("solid", fgColor="1F4E78")
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = header_fill
            for column_index, column in enumerate(frame.columns, start=1):
                values = [str(value) for value in frame[column].fillna("")]
                width = min(max([len(column), *(len(value) for value in values)]) + 2, 50)
                worksheet.column_dimensions[get_column_letter(column_index)].width = max(width, 12)
    else:
        raise ValueError("Output extension must be .csv, .xlsx, or .xlsm")
    return path
