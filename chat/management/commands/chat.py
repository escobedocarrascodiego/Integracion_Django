import json

import anthropic
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from chat import assistant, client
from chat.tools import ToolContext


class Command(BaseCommand):
    help = "Chat with the assistant in the terminal, as a demo user (a development shortcut: no login)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="maria.quispe@example.com", help="Demo user to chat as.")

    def handle(self, *args, email, **options):
        claude = client.get_client()
        if claude is None:
            raise CommandError("Set ANTHROPIC_API_KEY in .env first.")
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise CommandError(f"No user with email {email}")
        ctx = ToolContext(citizen_dni=user.dni)
        name = user.get_full_name() or user.email

        self.stdout.write(f"Chatting as {name} with {settings.ANTHROPIC_MODEL}. Type 'salir' to quit.\n")
        history: list[dict] = []
        while True:
            try:
                text = input("Tú: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text.lower() in ("salir", "exit", "quit"):
                break
            if not text:
                continue

            history.append({"role": "user", "content": text})
            try:
                result = assistant.reply(claude, history, ctx, citizen_name=name, model=settings.ANTHROPIC_MODEL)
            except anthropic.APIError as exc:
                history.pop()  # drop the unanswered question so the history stays valid
                self.stderr.write(self.style.ERROR(f"Claude API error: {_api_error_message(exc)}\n"))
                continue
            for call in result.tool_calls:
                status = "error" if call.is_error else "ok"
                arguments = json.dumps(call.input, ensure_ascii=False)
                self.stdout.write(self.style.HTTP_INFO(f"  [tool] {call.name}({arguments}) -> {status}"))
            self.stdout.write(f"Asistente: {result.reply}\n")
            history.append({"role": "assistant", "content": result.reply})


def _api_error_message(exc: anthropic.APIError) -> str:
    # Status errors carry the API's JSON body: {"type": "error", "error": {"message": ...}}
    body = getattr(exc, "body", None)
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return body["error"].get("message", str(exc))
    return str(exc)
