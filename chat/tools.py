"""The tools Claude can call, and the code that runs them.

Claude never touches the database: it asks for a tool by name with some
arguments, and run_tool() decides what actually happens. Each tool is a thin
wrapper over the service layer, and returns the same JSON as the REST API.

Security rule: anything that identifies the citizen (their DNI) comes from the
ToolContext, which the caller builds from the authenticated user. No tool takes a
DNI argument, so neither the model nor a prompt injection can ask for someone
else's complaints.
"""

import json
from dataclasses import dataclass

from municipal import services
from municipal.serializers import (
    ComplaintDetailSerializer,
    ComplaintSummarySerializer,
    ProcedureDetailSerializer,
    ProcedureSummarySerializer,
)


@dataclass(frozen=True)
class ToolContext:
    # Staff accounts have no DNI: their complaint queries simply find nothing.
    citizen_dni: str | None


class ToolError(Exception):
    """A problem Claude should hear about. Sent back as a tool_result with is_error=True."""


def _schema(properties: dict[str, dict]) -> dict:
    # strict tool use needs every property listed in "required" and no extra properties.
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


# What Claude sees. Descriptions say *when* to call each tool, not just what it does:
# that is what the model uses to decide.
TOOLS = [
    {
        "name": "search_procedures",
        "description": (
            "Search the municipality's catalogue of administrative procedures (trámites) by "
            "keywords. Returns each procedure's code, name, office, fee in soles and processing "
            "time. Call this whenever the citizen asks how to do something at the municipality, "
            "what a procedure costs or how long it takes. Keywords must be in Spanish (e.g. "
            "'licencia', 'partida'); pass an empty string to list every procedure."
        ),
        "strict": True,
        "input_schema": _schema(
            {"query": {"type": "string", "description": "Spanish keywords, or empty for all."}}
        ),
    },
    {
        "name": "get_procedure_details",
        "description": (
            "Get the full description and the ordered list of requirements of one procedure. "
            "Call this before telling the citizen which documents or requirements a procedure "
            "needs. Requires the procedure code; get it from search_procedures first."
        ),
        "strict": True,
        "input_schema": _schema(
            {"code": {"type": "string", "description": "Procedure code, e.g. LF-01."}}
        ),
    },
    {
        "name": "list_my_complaints",
        "description": (
            "List the complaints (reclamos) filed by the citizen you are talking to, newest "
            "first, with their current status. Call this when the citizen asks about their "
            "complaints without giving a tracking code."
        ),
        "strict": True,
        "input_schema": _schema({}),
    },
    {
        "name": "get_complaint_status",
        "description": (
            "Get one of the citizen's complaints with its full status history. Call this when "
            "the citizen asks about a specific complaint by its tracking code. Complaints filed "
            "by other people are reported as not found."
        ),
        "strict": True,
        "input_schema": _schema(
            {"tracking_code": {"type": "string", "description": "Tracking code, e.g. REC-2026-0001."}}
        ),
    },
]


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _search_procedures(ctx: ToolContext, query: str) -> str:
    return _json(ProcedureSummarySerializer(services.search_procedures(query), many=True).data)


def _get_procedure_details(ctx: ToolContext, code: str) -> str:
    procedure = services.get_procedure(code)
    if procedure is None:
        raise ToolError(f"There is no procedure with code {code!r}. Use search_procedures to find codes.")
    return _json(ProcedureDetailSerializer(procedure).data)


def _list_my_complaints(ctx: ToolContext) -> str:
    return _json(ComplaintSummarySerializer(services.list_complaints(ctx.citizen_dni), many=True).data)


def _get_complaint_status(ctx: ToolContext, tracking_code: str) -> str:
    complaint = services.get_complaint(tracking_code, ctx.citizen_dni)
    if complaint is None:
        raise ToolError(f"This citizen has no complaint with tracking code {tracking_code!r}.")
    return _json(ComplaintDetailSerializer(complaint).data)


_HANDLERS = {
    "search_procedures": _search_procedures,
    "get_procedure_details": _get_procedure_details,
    "list_my_complaints": _list_my_complaints,
    "get_complaint_status": _get_complaint_status,
}
_PARAMETERS = {tool["name"]: set(tool["input_schema"]["properties"]) for tool in TOOLS}


def run_tool(name: str, tool_input: dict, ctx: ToolContext) -> str:
    """Run the tool Claude asked for and return its result as a JSON string.

    Raises ToolError for anything Claude should be told about. Arguments are
    checked here even though strict mode already validates them: tool input is
    model output, and model output is never trusted blindly.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        raise ToolError(f"Unknown tool {name!r}.")
    if not isinstance(tool_input, dict) or set(tool_input) != _PARAMETERS[name]:
        raise ToolError(f"Invalid arguments for {name}; expected {sorted(_PARAMETERS[name])}.")
    if not all(isinstance(value, str) for value in tool_input.values()):
        raise ToolError(f"Every argument of {name} must be a string.")
    return handler(ctx, **tool_input)
