from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from web_scraper.config import load_config
from web_scraper.pipeline import run

ROOT = Path(__file__).parents[1]


def test_pipeline_reports_quality_and_exports_csv(tmp_path: Path) -> None:
    output = tmp_path / "faculty.csv"
    records, summary = run(load_config(ROOT / "configs/faculty.yaml"), str(output))
    assert len(records) == 3
    assert summary.extracted_rows == 4
    assert summary.duplicates_removed == 1
    assert summary.invalid_emails == 1
    assert summary.rows_with_missing_required_fields == 1
    frame = pd.read_csv(output)
    assert list(frame.columns) == [
        "name",
        "email",
        "job_title",
        "institution",
        "profile_url",
        "source_url",
        "scraped_at",
    ]


def test_excel_export_has_accessible_headers_filters_and_frozen_row(tmp_path: Path) -> None:
    output = tmp_path / "faculty.xlsx"
    run(load_config(ROOT / "configs/faculty.yaml"), str(output))
    sheet = load_workbook(output)["Scraped data"]
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter.ref == "A1:G4"
    assert not sheet.merged_cells.ranges
    assert sheet["A1"].value == "name"
    assert sheet.column_dimensions["A"].width >= 12
