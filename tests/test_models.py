import pytest
from django.contrib.auth import authenticate
from django.db import IntegrityError, connection, transaction

from accounts.models import User
from municipal.models import Complaint, ComplaintStatus, Procedure, Requirement
from municipal.sample_data import COMPLAINTS, DEMO_PASSWORD, DEMO_USERS, PROCEDURES, load_sample_data

pytestmark = pytest.mark.django_db


def test_sample_data_is_loaded(sample_data):
    assert User.objects.filter(dni__isnull=False).count() == len(DEMO_USERS)
    assert Procedure.objects.count() == len(PROCEDURES)
    assert Complaint.objects.count() == len(COMPLAINTS)
    assert Requirement.objects.count() == sum(len(p["requirements"]) for p in PROCEDURES)


def test_seed_can_run_twice_and_keeps_other_users(sample_data):
    User.objects.create_superuser(email="admin@example.com", password="not-a-real-password")

    load_sample_data()

    assert Procedure.objects.count() == len(PROCEDURES)
    assert User.objects.filter(email="admin@example.com").exists()


def test_requirements_come_back_in_order(sample_data):
    procedure = Procedure.objects.get(code="LF-01")

    positions = [r.position for r in procedure.requirements.all()]

    assert positions == [1, 2, 3, 4]


def test_complaint_status_matches_its_latest_event(sample_data):
    for complaint in Complaint.objects.prefetch_related("events"):
        events = list(complaint.events.all())
        assert complaint.status == events[-1].status
        assert complaint.updated_at == events[-1].created_at


def test_status_has_a_spanish_label(sample_data):
    complaint = Complaint.objects.get(tracking_code="REC-2026-0002")

    assert complaint.get_status_display() == "En evaluación"


def test_the_database_rejects_an_unknown_status(sample_data):
    # .update() skips Django's validation, like any other program writing to the
    # database would; the CHECK constraint still refuses it.
    with pytest.raises(IntegrityError), transaction.atomic():
        Complaint.objects.filter(tracking_code="REC-2026-0001").update(status="pendiente")


def test_status_is_stored_as_its_value(sample_data):
    with connection.cursor() as cursor:
        cursor.execute("SELECT status FROM municipal_complaint WHERE tracking_code = %s", ["REC-2026-0002"])
        [raw] = cursor.fetchone()

    assert raw == ComplaintStatus.IN_REVIEW.value == "in_review"


def test_demo_users_log_in_with_their_email_in_any_case(sample_data):
    user = authenticate(email="Maria.Quispe@Example.com", password=DEMO_PASSWORD)

    assert user is not None
    assert user.dni == "70000001"
    assert authenticate(email="maria.quispe@example.com", password="wrong") is None


def test_superuser_needs_no_username_or_dni():
    admin = User.objects.create_superuser(email="Admin@Example.com", password="not-a-real-password")

    assert admin.email == "admin@example.com"
    assert admin.is_staff and admin.is_superuser
    assert admin.dni is None
