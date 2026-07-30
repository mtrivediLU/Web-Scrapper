import csv
from pathlib import Path

from web_scraper.exporters import export_rows
from web_scraper.uoregon import (
    COLUMNS,
    FacultyRecord,
    alphabetical_page_urls,
    deduplicate,
    parse_directory_page,
)

SOURCE_URL = "https://cas.uoregon.edu/directory/computer-science-faculty"
HTML = """
<div class="pager-alphabetical">
  <a href="/directory/computer-science-faculty/A">A</a>
  <a href="/directory/computer-science-faculty/C">C</a>
  <a href="/directory/computer-science-faculty/A">Again</a>
</div>
<div class="view-content">
  <div class="listing__row">
    <h2 class="views-field-lname"><a
      href="/directory/computer-science-faculty/all/oneil">Anne-Marie O'Neil</a></h2>
    <div class="views-field-job-title"><span class="field-content">Professor</span></div>
    <div class="views-field-job-title2"><span class="field-content">Department Head</span></div>
    <div class="views-field-email"><a href="mailto:ANNE.O'NEIL@uoregon.edu">Email</a></div>
  </div>
  <div class="listing__row">
    <h2 class="views-field-lname"><a
      href="/directory/computer-science-faculty/all/lee">Jo Lee</a></h2>
    <div class="views-field-job-title"><span class="field-content">Teaching Professor</span></div>
  </div>
  <div class="listing__row"><div>Decorative empty row</div></div>
</div>
"""


def test_parsing_preserves_name_punctuation_blanks_and_absolute_urls() -> None:
    records = parse_directory_page(HTML, SOURCE_URL)
    assert len(records) == 2
    first = records[0]
    assert first.first_name == "Anne-Marie"
    assert first.last_name == "O'Neil"
    assert first.title == "Professor | Department Head"
    assert first.email == "anne.o'neil@uoregon.edu"
    assert (
        first.profile_url == "https://cas.uoregon.edu/directory/computer-science-faculty/all/oneil"
    )
    assert records[1].email == ""
    assert all(None not in record.as_row().values() for record in records)


def test_alphabetical_pagination_urls_are_absolute_and_unique() -> None:
    assert alphabetical_page_urls(HTML, SOURCE_URL) == [
        "https://cas.uoregon.edu/directory/computer-science-faculty/A",
        "https://cas.uoregon.edu/directory/computer-science-faculty/C",
    ]


def test_column_order_and_deduplication_use_email_then_profile() -> None:
    first = FacultyRecord(
        "Ada", "Lovelace", "Professor", "Computer Science", "ada@uoregon.edu", "", SOURCE_URL
    )
    duplicate = FacultyRecord(
        "Ada", "Lovelace", "Professor", "Computer Science", "ADA@uoregon.edu", "x", SOURCE_URL
    )
    no_email = FacultyRecord(
        "Grace",
        "Hopper",
        "Professor",
        "Computer Science",
        "",
        "https://example.edu/grace",
        SOURCE_URL,
    )
    records, removed = deduplicate([first, duplicate, no_email])
    assert COLUMNS == [
        "first_name",
        "last_name",
        "title",
        "department",
        "email",
        "profile_url",
        "source_url",
    ]
    assert records == [first, no_email]
    assert removed == 1


def test_target_csv_has_exact_column_order_and_blank_values(tmp_path: Path) -> None:
    record = FacultyRecord(
        "Ram", "Durairajan", "Professor", "Computer Science", "", "url", "source"
    )
    output = tmp_path / "faculty.csv"
    export_rows([record.as_row()], output, COLUMNS, "Faculty")
    with output.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == COLUMNS
    assert rows == [{**record.as_row(), "email": ""}]
