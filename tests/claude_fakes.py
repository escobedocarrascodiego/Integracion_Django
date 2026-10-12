"""A stand-in for the Claude API, so chat tests run offline, for free and deterministically.

Responses are real SDK objects (BetaMessage), built from the same JSON shape the
API returns, so the code under test can't tell the difference.
"""

import copy
import itertools
from types import SimpleNamespace

from anthropic.types.beta import BetaMessage

_ids = itertools.count(1)


class FakeClaude:
    """Returns queued responses in order and records every request it receives."""

    def __init__(self) -> None:
        self.responses: list = []
        self.requests: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def queue(self, *responses) -> None:
        self.responses.extend(responses)

    def _create(self, **request):
        # Snapshot: the code under test keeps appending to the same messages list.
        self.requests.append(copy.deepcopy(request))
        assert self.responses, "FakeClaude received a request nobody queued a response for"
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _message(content: list[dict], stop_reason: str) -> BetaMessage:
    return BetaMessage.model_validate(
        {
            "id": f"msg_{next(_ids)}",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }
    )


def text_response(text: str) -> BetaMessage:
    return _message([{"type": "text", "text": text}], "end_turn")


def tool_use_response(*calls: tuple[str, dict]) -> BetaMessage:
    """Claude asking for one or more tools: (name, input) pairs."""
    # Real responses usually start with a thinking block; it must be sent back untouched.
    content = [{"type": "thinking", "thinking": "", "signature": "fake-signature"}]
    content += [
        {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": tool_input}
        for name, tool_input in calls
    ]
    return _message(content, "tool_use")


def refusal_response() -> BetaMessage:
    return _message([], "refusal")
