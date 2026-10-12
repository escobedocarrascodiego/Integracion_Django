import pytest

from accounts.models import User
from municipal.sample_data import load_sample_data


@pytest.fixture
def sample_data(db):
    # `db` is pytest-django's fixture: the test runs inside a transaction that is
    # rolled back afterwards, on a test database it creates and destroys itself.
    load_sample_data()


@pytest.fixture
def staff_client(client, db):
    """A test client logged in as a superuser, for the admin pages."""
    admin = User.objects.create_superuser(email="admin@example.com", password="not-a-real-password")
    client.force_login(admin)
    return client
