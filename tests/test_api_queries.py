import pytest

pytestmark = pytest.mark.django_db


def test_health(api_client):
    assert api_client.get("/api/health/").json() == {"status": "ok"}


def test_procedures_are_public_and_searchable(api_client, sample_data):
    response = api_client.get("/api/procedures/", {"q": "licencia anuncio"})

    assert response.status_code == 200
    assert [p["code"] for p in response.json()] == ["AP-01"]


def test_procedure_detail(api_client, sample_data):
    response = api_client.get("/api/procedures/LF-01/")

    body = response.json()
    assert body["fee"] == "98.50"  # money travels as a string, never as a float
    assert body["requirements"][-1] == "Pago del derecho de trámite."
    assert "trámite" in response.content.decode()  # not escaped as á


def test_unknown_procedure_is_404(api_client, sample_data):
    response = api_client.get("/api/procedures/XX-99/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Trámite no encontrado."}


def test_complaints_require_login(api_client, sample_data):
    assert api_client.get("/api/complaints/").status_code == 401
    assert api_client.get("/api/complaints/REC-2026-0001/").status_code == 401


def test_complaint_list_only_includes_my_own(api_client, login):
    response = api_client.get("/api/complaints/", headers=login("jose.mamani@example.com"))

    assert [c["tracking_code"] for c in response.json()] == ["REC-2026-0004", "REC-2026-0003"]


def test_complaint_detail(api_client, login):
    body = api_client.get("/api/complaints/REC-2026-0001/", headers=login()).json()

    assert body["status"] == "resolved"
    assert body["status_label"] == "Atendido"
    assert body["created_at"] == "2026-09-02T08:15:00-05:00"  # Lima time
    assert [e["status"] for e in body["events"]] == ["received", "forwarded", "resolved"]


def test_someone_elses_complaint_looks_like_it_does_not_exist(api_client, login):
    response = api_client.get("/api/complaints/REC-2026-0003/", headers=login())  # José's, as María

    assert response.status_code == 404
    assert response.json() == {"detail": "Reclamo no encontrado."}
