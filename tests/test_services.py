import pytest

from municipal import services
from municipal.sample_data import PROCEDURES

pytestmark = pytest.mark.django_db

MARIA_DNI = "70000001"


def procedure_codes(query: str = "") -> list[str]:
    return [p.code for p in services.search_procedures(query)]


def test_search_without_query_returns_the_whole_catalogue(sample_data):
    assert len(procedure_codes()) == len(PROCEDURES)


def test_search_requires_every_word_to_match(sample_data):
    assert procedure_codes("licencia") == ["AP-01", "LF-01"]
    assert procedure_codes("LICENCIA anuncio") == ["AP-01"]


def test_search_treats_wildcards_as_plain_text(sample_data):
    assert procedure_codes("%") == []


def test_procedure_lookup_ignores_case_and_spaces(sample_data):
    procedure = services.get_procedure(" lf-01 ")

    assert procedure.code == "LF-01"
    assert procedure.requirements.count() == 4


def test_unknown_procedure_returns_none(sample_data):
    assert services.get_procedure("XX-99") is None


def test_citizens_only_see_their_own_complaints_newest_first(sample_data):
    codes = [c.tracking_code for c in services.list_complaints(MARIA_DNI)]

    assert codes == ["REC-2026-0002", "REC-2026-0001"]


def test_someone_elses_complaint_is_indistinguishable_from_a_missing_one(sample_data):
    assert services.get_complaint("REC-2026-0003", MARIA_DNI) is None  # José's
    assert services.get_complaint("REC-2099-9999", MARIA_DNI) is None
