"""`manage.py chat`: the terminal chat, fed with scripted input."""

from io import StringIO

import anthropic
import httpx2
import pytest
from claude_fakes import text_response
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def run_chat(monkeypatch, *typed: str) -> tuple[str, str]:
    lines = iter(typed)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(lines))
    out, err = StringIO(), StringIO()
    call_command("chat", stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


def test_chat_command_answers(monkeypatch, sample_data, fake_claude):
    fake_claude.queue(text_response("¡Hola María!"))

    out, _ = run_chat(monkeypatch, "Hola", "salir")

    assert "Asistente: ¡Hola María!" in out


def test_chat_command_survives_api_errors(monkeypatch, sample_data, fake_claude):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    error_body = {"type": "error", "error": {"type": "invalid_request_error", "message": "Bad key"}}
    fake_claude.queue(
        anthropic.BadRequestError("Error code: 400", response=httpx2.Response(400, request=request), body=error_body),
        text_response("Ahora sí."),
    )

    out, err = run_chat(monkeypatch, "Hola", "Hola otra vez", "salir")

    assert "Claude API error: Bad key" in err
    assert "Asistente: Ahora sí." in out
    # The failed question was dropped, so the retry sends a clean history.
    assert fake_claude.requests[1]["messages"] == [{"role": "user", "content": "Hola otra vez"}]
