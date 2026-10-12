"""Business queries shared by every interface: the REST API, and later the chat
tools and the MCP server. They return model instances and know nothing about
HTTP, serializers or LLMs.
"""

from django.db.models import Q, QuerySet

from municipal.models import Complaint, Procedure


def search_procedures(query: str = "", limit: int = 20) -> QuerySet[Procedure]:
    """Procedures whose code, name or description contain every word of `query`.

    Without a query, returns the whole catalogue (up to `limit`).
    """
    procedures = Procedure.objects.all()
    for term in query.split():
        # icontains escapes % and _, so a user typing them searches for those characters.
        procedures = procedures.filter(
            Q(code__icontains=term) | Q(name__icontains=term) | Q(description__icontains=term)
        )
    return procedures.order_by("name")[:limit]


def get_procedure(code: str) -> Procedure | None:
    return Procedure.objects.prefetch_related("requirements").filter(code=code.strip().upper()).first()


# Complaint queries always require the citizen's DNI and only return that
# citizen's complaints. The caller decides where the DNI comes from: the API
# takes it from the logged-in user, never from the request or from the model.


def list_complaints(citizen_dni: str) -> QuerySet[Complaint]:
    """The citizen's complaints, newest first."""
    return Complaint.objects.filter(citizen_dni=citizen_dni).order_by("-created_at")


def get_complaint(tracking_code: str, citizen_dni: str) -> Complaint | None:
    """A complaint with its history, or None.

    None covers both "doesn't exist" and "belongs to someone else", so callers
    can't use this to find out which tracking codes exist.
    """
    return (
        Complaint.objects.prefetch_related("events")
        .filter(tracking_code=tracking_code.strip().upper(), citizen_dni=citizen_dni)
        .first()
    )
