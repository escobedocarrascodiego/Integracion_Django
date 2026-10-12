import pytest
from rest_framework.test import APIClient

from accounts.models import User
from municipal.sample_data import DEMO_PASSWORD, load_sample_data


@pytest.fixture
def sample_data(db):
    # `db` is pytest-django's fixture: the test runs inside a transaction that is
    # rolled back afterwards, on a test database it creates and destroys itself.
    load_sample_data()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def login(api_client, sample_data):
    """Log in as a demo user and return the Authorization header to send with requests."""

    def _login(email: str = "maria.quispe@example.com") -> dict[str, str]:
        response = api_client.post("/api/auth/login/", {"email": email, "password": DEMO_PASSWORD}, format="json")
        assert response.status_code == 200, response.data
        return {"Authorization": f"Bearer {response.data['access']}"}

    return _login


@pytest.fixture
def staff_client(client, db):
    """A test client logged in as a superuser, for the admin pages."""
    admin = User.objects.create_superuser(email="admin@example.com", password="not-a-real-password")
    client.force_login(admin)
    return client
