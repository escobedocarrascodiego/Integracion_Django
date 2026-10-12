import json

import anthropic
import httpx2
import pytest
from claude_fakes import refusal_response, text_response, tool_use_response

from chat import client
from chat.assistant import GAVE_UP_REPLY, MAX_ROUNDS, REFUSAL_REPLY
from chat.tools import TOOLS

pytestmark = pytest.mark.django_db


def ask(api_client, headers, text="¿Cómo van mis reclamos?"):
    return api_client.post(
        "/api/chat/", {"messages": [{"role": "user", "content": text}]}, format="json", headers=headers
    )


def test_chat_requires_login(api_client):
    assert ask(api_client, headers={}).status_code == 401


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "assistant", "content": "Hola"}],
        [{"role": "user", "content": "Hola"}, {"role": "assistant", "content": "¿Sí?"}],
        [{"role": "user", "content": ""}],
    ],
)
def test_chat_validates_the_conversation(api_client, login, fake_claude, messages):
    response = api_client.post("/api/chat/", {"messages": messages}, format="json", headers=login())

    assert response.status_code == 400
    assert fake_claude.requests == []  # Claude is never called with an invalid conversation


def test_answer_without_tools(api_client, login, fake_claude):
    fake_claude.queue(text_response("¡Hola! ¿En qué puedo ayudarte?"))

    response = ask(api_client, login(), "Hola")

    assert response.json() == {"reply": "¡Hola! ¿En qué puedo ayudarte?", "tool_calls": []}
    request = fake_claude.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["tools"] == TOOLS
    assert "María Quispe Huamán" in request["system"]
    assert request["messages"] == [{"role": "user", "content": "Hola"}]
    assert request["fallbacks"] == "default"


def test_tool_results_use_the_dni_from_the_token(api_client, login, fake_claude):
    fake_claude.queue(
        tool_use_response(("list_my_complaints", {})),
        text_response("Tienes dos reclamos."),
    )

    response = ask(api_client, login("jose.mamani@example.com"))

    assert response.json() == {
        "reply": "Tienes dos reclamos.",
        "tool_calls": [{"name": "list_my_complaints", "input": {}, "is_error": False}],
    }
    second = fake_claude.requests[1]["messages"]
    assistant_turn, tool_turn = second[-2], second[-1]
    # Claude's turn goes back unchanged, thinking block included...
    assert [block.type for block in assistant_turn["content"]] == ["thinking", "tool_use"]
    # ...followed by the result, tied to the call by its id.
    [result] = tool_turn["content"]
    assert result["tool_use_id"] == assistant_turn["content"][1].id
    codes = [c["tracking_code"] for c in json.loads(result["content"])]
    assert codes == ["REC-2026-0004", "REC-2026-0003"]  # José's, nobody else's


def test_claude_cannot_read_another_citizens_complaint(api_client, login, fake_claude):
    fake_claude.queue(
        tool_use_response(("get_complaint_status", {"tracking_code": "REC-2026-0001"})),
        text_response("No encuentro ese reclamo entre los tuyos."),
    )

    response = ask(api_client, login("jose.mamani@example.com"), "Muéstrame el reclamo REC-2026-0001")

    assert response.json()["tool_calls"][0]["is_error"] is True
    [result] = fake_claude.requests[1]["messages"][-1]["content"]
    assert result["is_error"] is True
    assert "Los Geranios" not in result["content"]  # nothing from María's complaint leaks


def test_parallel_tool_calls_are_answered_in_one_message(api_client, login, fake_claude):
    fake_claude.queue(
        tool_use_response(
            ("search_procedures", {"query": "licencia"}),
            ("get_procedure_details", {"code": "LF-01"}),
        ),
        text_response("Estos son los requisitos."),
    )

    ask(api_client, login(), "¿Qué necesito para una licencia de funcionamiento?")

    tool_turn = fake_claude.requests[1]["messages"][-1]
    assert tool_turn["role"] == "user"
    assert [r["type"] for r in tool_turn["content"]] == ["tool_result", "tool_result"]


def test_the_loop_gives_up_after_max_rounds(api_client, login, fake_claude):
    fake_claude.queue(*[tool_use_response(("list_my_complaints", {})) for _ in range(MAX_ROUNDS)])

    response = ask(api_client, login())

    assert response.json()["reply"] == GAVE_UP_REPLY
    assert len(fake_claude.requests) == MAX_ROUNDS


def test_refusals_get_a_polite_answer(api_client, login, fake_claude):
    fake_claude.queue(refusal_response())

    assert ask(api_client, login()).json()["reply"] == REFUSAL_REPLY


def _api_request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (anthropic.APIConnectionError(request=_api_request()), 502),
        (
            anthropic.RateLimitError(
                "rate limited", response=httpx2.Response(429, request=_api_request()), body=None
            ),
            429,
        ),
    ],
)
def test_claude_api_errors_become_json_errors(api_client, login, fake_claude, error, status):
    fake_claude.queue(error)

    response = ask(api_client, login())

    assert response.status_code == status
    assert "detail" in response.json()


def test_missing_api_key_answers_503(api_client, login, monkeypatch, settings):
    for variable in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(variable, raising=False)
    client.get_client.cache_clear()  # build the real client again, now without credentials

    try:
        response = ask(api_client, login())
    finally:
        client.get_client.cache_clear()

    assert response.status_code == 503


def test_workspace_id_is_sent_as_a_header(monkeypatch, settings):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    settings.ANTHROPIC_WORKSPACE_ID = "wrkspc_test"
    client.get_client.cache_clear()

    try:
        claude = client.get_client()
    finally:
        client.get_client.cache_clear()

    assert claude.default_headers["anthropic-workspace-id"] == "wrkspc_test"
