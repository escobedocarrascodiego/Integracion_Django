import logging
from functools import cache

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)


@cache
def get_client() -> anthropic.Anthropic | None:
    """The shared Claude client, or None if no credentials are configured.

    Callers use it as `client.get_client()` (through the module), so tests can
    replace it with one that returns a fake client.
    """
    workspace_id = settings.ANTHROPIC_WORKSPACE_ID
    # Reads ANTHROPIC_API_KEY (or other supported credentials) from the environment.
    client = anthropic.Anthropic(
        default_headers={"anthropic-workspace-id": workspace_id} if workspace_id else None
    )
    if client.api_key is None and client.auth_token is None and client.credentials is None:
        logger.warning("No Claude credentials: set ANTHROPIC_API_KEY in .env")
        return None
    return client
