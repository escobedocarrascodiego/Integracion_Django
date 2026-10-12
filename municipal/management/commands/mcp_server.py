from django.core.management.base import BaseCommand

from municipal.mcp_server import create_server


class Command(BaseCommand):
    help = "Run the MCP server over stdio, for hosts such as Claude Desktop or Claude Code."

    # Skip the system checks: over stdio, stdout is the protocol channel, and
    # nothing but protocol messages may be written to it.
    requires_system_checks = []

    def handle(self, *args, **options):
        # A management command starts with Django already set up (settings loaded,
        # apps ready), which is why the server lives here and not in a loose script.
        create_server().run()  # stdio is the default transport
