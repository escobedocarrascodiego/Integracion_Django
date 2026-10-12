"""MCP server: the municipality's queries as tools for any MCP host.

Started with `python manage.py mcp_server`. Hosts such as Claude Desktop or
Claude Code launch it as a subprocess and talk to it over stdin/stdout (the
stdio transport). The host runs the model and the tool loop; this server only
describes its tools and runs them. It never calls Claude and needs no API key.

Like the REST API and the chat, it is a thin adapter over municipal/services.py,
and it returns the same JSON as the API (the same serializers).

Never print() here: over stdio, stdout carries the protocol itself.
"""

import json
from functools import wraps
from typing import Annotated, Any

from django.db import connection
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from municipal import services
from municipal.serializers import ComplaintDetailSerializer, ProcedureDetailSerializer, ProcedureSummarySerializer

INSTRUCTIONS = """\
Tools for the citizen-service office of the Municipalidad Distrital de Ejemplo (Peru).
Use them to answer questions about municipal procedures (requirements, fees in soles,
processing time in business days, responsible office) and about the status of a
citizen complaint. Never make up requirements, fees or statuses: get them from the tools.
"""

# Hints for the host: these tools only read data, so it can run them without
# asking the user for confirmation every time.
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def closes_db_connection(func):
    """Close this thread's database connection when the call ends.

    Django closes connections at the end of every HTTP request, but this process
    serves no HTTP requests and runs for hours, so it has to do it itself.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            connection.close()

    return wrapper


def create_server() -> MCPServer:
    mcp = MCPServer("muni-assistant-django", instructions=INSTRUCTIONS)

    # Each tool is a plain function: its name is the tool name, its docstring is the
    # description the model reads, and its type hints become the input schema. Sync
    # functions run in a worker thread, outside the event loop, which is what lets
    # them use Django's ORM (it refuses to run inside async code).

    @mcp.tool(annotations=READ_ONLY)
    @closes_db_connection
    def search_procedures(
        query: Annotated[
            str, Field(description="Spanish keywords, e.g. 'licencia' or 'partida'. Empty lists every procedure.")
        ] = "",
    ) -> list[dict[str, Any]]:
        """Search the municipality's catalogue of administrative procedures (trámites).

        Call this whenever someone asks how to do something at the municipality, what a
        procedure costs or how long it takes. Returns each procedure's code, name,
        office, fee in soles and processing time.
        """
        return ProcedureSummarySerializer(services.search_procedures(query), many=True).data

    @mcp.tool(annotations=READ_ONLY)
    @closes_db_connection
    def get_procedure_details(
        code: Annotated[str, Field(description="Procedure code, e.g. LF-01.")],
    ) -> dict[str, Any]:
        """Get the full description and the ordered requirements of one procedure.

        Call this before telling someone which documents a procedure needs. Get the
        code from search_procedures first.
        """
        procedure = services.get_procedure(code)
        if procedure is None:
            # ToolError: the model sees this message and can recover (e.g. search first).
            raise ToolError(f"There is no procedure with code {code!r}. Use search_procedures to find codes.")
        return ProcedureDetailSerializer(procedure).data

    @mcp.tool(annotations=READ_ONLY)
    @closes_db_connection
    def get_complaint_status(
        tracking_code: Annotated[str, Field(description="Tracking code, e.g. REC-2026-0001.")],
        dni: Annotated[str, Field(description="DNI of the person who filed it.", pattern=r"^\d{8}$")],
    ) -> dict[str, Any]:
        """Get a citizen complaint (reclamo) with its full status history.

        Requires both the tracking code and the DNI of the person who filed it, like
        the municipality's public complaint lookup. If you don't have both, ask the
        citizen for them; never guess a DNI.
        """
        # Without a login, knowing both values is what proves the right to see it.
        # The service is the same one the API uses; only the DNI's source differs.
        complaint = services.get_complaint(tracking_code, dni)
        if complaint is None:
            raise ToolError("No complaint matches that tracking code and DNI.")
        return ComplaintDetailSerializer(complaint).data

    @mcp.resource(
        "tupa://procedures",
        name="procedure-catalog",
        title="Catálogo de trámites (TUPA)",
        description="Every municipal procedure with its fee, processing time and office.",
        mime_type="application/json",
    )
    @closes_db_connection
    def procedure_catalog() -> str:
        # A resource is data the user attaches as context, rather than an action the
        # model decides to take.
        catalog = ProcedureSummarySerializer(services.search_procedures(), many=True).data
        return json.dumps(catalog, ensure_ascii=False, indent=2)

    @mcp.prompt(title="Consultar un trámite")
    def ask_about_procedure(
        procedure: Annotated[str, Field(description="What the citizen wants to do, e.g. 'abrir una bodega'.")],
    ) -> str:
        """A ready-made question about a municipal procedure, for the user to pick from a menu."""
        return (
            f"Quiero hacer este trámite en la municipalidad: {procedure}. "
            "¿Qué requisitos necesito, cuánto cuesta, cuánto demora y en qué oficina se hace? "
            "Usa las herramientas de la municipalidad para responder."
        )

    return mcp
