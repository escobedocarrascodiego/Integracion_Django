from dataclasses import asdict

import anthropic
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat import assistant, client
from chat.tools import ToolContext

UNAVAILABLE = "El asistente no está disponible en este momento. Intenta más tarde."


class ChatTurnSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=4000)


class ChatRequestSerializer(serializers.Serializer):
    """The conversation so far, as plain text turns. The client keeps the history
    and sends it on every request (like the Claude API itself), so the server
    stores nothing between turns.
    """

    messages = ChatTurnSerializer(many=True, allow_empty=False, max_length=40)

    def validate_messages(self, messages):
        if messages[0]["role"] != "user" or messages[-1]["role"] != "user":
            raise serializers.ValidationError("La conversación debe empezar y terminar con un mensaje del usuario.")
        return messages


class ChatView(APIView):
    """POST {messages: [...]} -> {reply, tool_calls}. Requires a login (the default permission)."""

    def post(self, request):
        body = ChatRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        claude = client.get_client()
        if claude is None:
            return Response({"detail": UNAVAILABLE}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # The DNI comes from the logged-in user, never from the request or from Claude.
        ctx = ToolContext(citizen_dni=request.user.dni)
        try:
            result = assistant.reply(
                claude,
                [dict(turn) for turn in body.validated_data["messages"]],
                ctx,
                citizen_name=request.user.get_full_name() or request.user.email,
                model=settings.ANTHROPIC_MODEL,
            )
        # Most specific first: each failure means something different to the caller.
        except anthropic.AuthenticationError:
            assistant.logger.exception("Claude rejected the API key; check ANTHROPIC_API_KEY")
            return Response({"detail": UNAVAILABLE}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except anthropic.RateLimitError:
            return Response(
                {"detail": "El asistente está ocupado. Intenta de nuevo en un momento."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except (anthropic.APIStatusError, anthropic.APIConnectionError):
            assistant.logger.exception("Claude API call failed")
            return Response({"detail": UNAVAILABLE}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"reply": result.reply, "tool_calls": [asdict(call) for call in result.tool_calls]})
