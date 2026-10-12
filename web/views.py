"""The web page: a small single-page app that uses the same REST API as any other client."""

from django.shortcuts import render

# The page displays model output, so lock it down: only scripts, styles and images
# served by this app may load (no inline scripts, nothing from other origins). Even
# if some text slipped through as HTML, the browser would refuse to run it.
CONTENT_SECURITY_POLICY = "default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


def home(request):
    response = render(request, "web/index.html")
    response["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    return response
