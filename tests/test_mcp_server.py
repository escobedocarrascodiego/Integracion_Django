"""The MCP server, exercised through the SDK's own client, connected in memory.

The tools run in a worker thread with its own database connection, which can't
see data inside another connection's open transaction. So these tests use
transaction=True: the sample data is really committed, and pytest-django empties
the tables after each test.
"""

import json

import pytest
from mcp import Client

from municipal.mcp_server import create_server

pytestmark = [pytest.mark.anyio, pytest.mark.django_db(transaction=True)]

MARIA_DNI = "70000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def mcp_client(sample_data):
    async with Client(create_server()) as client:
        yield client


async def test_exposes_three_read_only_tools(mcp_client):
    tools = (await mcp_client.list_tools()).tools

    assert {t.name for t in tools} == {"search_procedures", "get_procedure_details", "get_complaint_status"}
    assert all(t.annotations.read_only_hint for t in tools)
    assert all(t.description for t in tools)  # the docstrings, which the model reads


async def test_schemas_come_from_the_type_hints(mcp_client):
    tools = {t.name: t for t in (await mcp_client.list_tools()).tools}

    schema = tools["get_complaint_status"].input_schema
    assert schema["required"] == ["tracking_code", "dni"]
    assert schema["properties"]["dni"]["pattern"] == r"^\d{8}$"


async def test_search_procedures(mcp_client):
    result = await mcp_client.call_tool("search_procedures", {"query": "licencia anuncio"})

    assert not result.is_error
    assert [p["code"] for p in result.structured_content["result"]] == ["AP-01"]


async def test_procedure_details_match_the_rest_api(mcp_client):
    result = await mcp_client.call_tool("get_procedure_details", {"code": "LF-01"})

    assert result.structured_content["fee"] == "98.50"
    assert result.structured_content["requirements"][-1] == "Pago del derecho de trámite."


async def test_unknown_procedure_is_an_error_the_model_can_read(mcp_client):
    result = await mcp_client.call_tool("get_procedure_details", {"code": "XX-99"})

    assert result.is_error
    assert "search_procedures" in result.content[0].text


async def test_complaint_with_matching_dni(mcp_client):
    result = await mcp_client.call_tool(
        "get_complaint_status", {"tracking_code": "rec-2026-0001", "dni": MARIA_DNI}
    )

    assert not result.is_error
    assert result.structured_content["status_label"] == "Atendido"
    assert len(result.structured_content["events"]) == 3


async def test_complaint_needs_the_dni_of_whoever_filed_it(mcp_client):
    result = await mcp_client.call_tool(
        "get_complaint_status", {"tracking_code": "REC-2026-0001", "dni": "70000002"}  # José's DNI
    )

    assert result.is_error
    assert "Los Geranios" not in result.content[0].text  # nothing from María's complaint leaks


async def test_dni_format_is_validated(mcp_client):
    result = await mcp_client.call_tool("get_complaint_status", {"tracking_code": "REC-2026-0001", "dni": "1234"})

    assert result.is_error


async def test_procedure_catalog_resource(mcp_client):
    contents = (await mcp_client.read_resource("tupa://procedures")).contents

    assert len(json.loads(contents[0].text)) == 6


async def test_procedure_prompt(mcp_client):
    prompt = await mcp_client.get_prompt("ask_about_procedure", {"procedure": "abrir una bodega"})

    [message] = prompt.messages
    assert message.role == "user"
    assert "abrir una bodega" in message.content.text
