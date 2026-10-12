import json

import pytest

from chat.tools import TOOLS, ToolContext, ToolError, run_tool

pytestmark = pytest.mark.django_db

JOSE = ToolContext(citizen_dni="70000002")


def test_tool_schemas_are_valid_for_strict_mode():
    for tool in TOOLS:
        schema = tool["input_schema"]
        assert tool["strict"] is True
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"]), tool["name"]


def test_no_tool_lets_the_model_choose_whose_data_to_read():
    for tool in TOOLS:
        assert "dni" not in json.dumps(tool["input_schema"]).lower(), tool["name"]


def test_search_procedures(sample_data):
    result = json.loads(run_tool("search_procedures", {"query": "partida"}, JOSE))

    assert [p["code"] for p in result] == ["RC-02"]


def test_procedure_details(sample_data):
    result = json.loads(run_tool("get_procedure_details", {"code": "CN-01"}, JOSE))

    assert len(result["requirements"]) == 4


def test_unknown_procedure_is_reported_to_claude(sample_data):
    with pytest.raises(ToolError, match="search_procedures"):
        run_tool("get_procedure_details", {"code": "XX-99"}, JOSE)


def test_list_my_complaints_only_returns_the_citizens_own(sample_data):
    result = json.loads(run_tool("list_my_complaints", {}, JOSE))

    assert [c["tracking_code"] for c in result] == ["REC-2026-0004", "REC-2026-0003"]
    assert result[0]["status_label"] == "Registrado"  # Claude gets the Spanish label too


def test_someone_elses_complaint_is_not_found(sample_data):
    with pytest.raises(ToolError, match="no complaint"):
        run_tool("get_complaint_status", {"tracking_code": "REC-2026-0001"}, JOSE)  # María's


def test_a_user_without_dni_sees_no_complaints(sample_data):
    assert json.loads(run_tool("list_my_complaints", {}, ToolContext(citizen_dni=None))) == []


def test_an_extra_dni_argument_is_rejected(sample_data):
    with pytest.raises(ToolError, match="Invalid arguments"):
        run_tool(
            "get_complaint_status",
            {"tracking_code": "REC-2026-0001", "citizen_dni": "70000001"},
            JOSE,
        )


def test_non_string_arguments_are_rejected():
    with pytest.raises(ToolError, match="must be a string"):
        run_tool("search_procedures", {"query": ["licencia"]}, JOSE)


def test_unknown_tool():
    with pytest.raises(ToolError, match="Unknown tool"):
        run_tool("drop_tables", {}, JOSE)
