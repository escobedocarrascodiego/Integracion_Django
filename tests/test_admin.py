"""Smoke tests for the admin: every page we configured renders."""

import pytest
from django.urls import reverse

from municipal.models import Complaint, Procedure

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "url_name",
    ["admin:municipal_procedure_changelist", "admin:municipal_complaint_changelist", "admin:accounts_user_changelist"],
)
def test_changelists_render(staff_client, sample_data, url_name):
    assert staff_client.get(reverse(url_name)).status_code == 200


def test_procedure_page_shows_its_requirements_inline(staff_client, sample_data):
    procedure = Procedure.objects.get(code="LF-01")

    response = staff_client.get(reverse("admin:municipal_procedure_change", args=[procedure.pk]))

    assert response.status_code == 200
    assert "Pago del derecho de trámite." in response.content.decode()


def test_complaint_search_by_dni(staff_client, sample_data):
    response = staff_client.get(reverse("admin:municipal_complaint_changelist"), {"q": "70000002"})

    page = response.content.decode()
    assert "REC-2026-0003" in page
    assert "REC-2026-0001" not in page


def test_complaint_page_shows_its_history(staff_client, sample_data):
    complaint = Complaint.objects.get(tracking_code="REC-2026-0001")

    response = staff_client.get(reverse("admin:municipal_complaint_change", args=[complaint.pk]))

    assert "Se reprogramó la ruta de recolección" in response.content.decode()


def test_add_user_form_renders(staff_client):
    assert staff_client.get(reverse("admin:accounts_user_add")).status_code == 200


def test_admin_requires_staff(client, sample_data):
    response = client.get(reverse("admin:municipal_complaint_changelist"))

    assert response.status_code == 302  # redirected to the admin login
