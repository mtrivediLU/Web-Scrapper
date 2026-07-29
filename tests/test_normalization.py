from web_scraper.models import PersonRecord
from web_scraper.normalization import clean_text, deduplicate, normalize, valid_email


def test_normalization_collapses_whitespace_and_email() -> None:
    record = normalize(
        PersonRecord(name="  Dr.  Ada\xa0Lovelace ", email="mailto: ADA@EXAMPLE.EDU ")
    )
    assert record.name == "Dr. Ada Lovelace"
    assert record.email == "ada@example.edu"
    assert clean_text(" a\n b ") == "a b"


def test_email_validation_allows_missing_but_flags_malformed() -> None:
    assert valid_email("")
    assert valid_email("ada@example.edu")
    assert not valid_email("ada.example.edu")


def test_deduplication_prefers_email_then_profile() -> None:
    first = PersonRecord(name="Ada", email="ada@example.edu")
    duplicate = PersonRecord(name="Ada Lovelace", email="ada@example.edu")
    profile_only = PersonRecord(name="Grace", profile_url="https://example.edu/grace")
    records, removed = deduplicate([first, duplicate, profile_only])
    assert records == [first, profile_only]
    assert removed == 1
