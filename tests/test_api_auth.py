from datetime import timedelta

import jwt as pyjwt
import pytest
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from municipal.sample_data import DEMO_PASSWORD

pytestmark = pytest.mark.django_db

MARIA = {"email": "maria.quispe@example.com", "password": DEMO_PASSWORD}


def bearer(token) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_an_access_and_a_refresh_token(api_client, sample_data):
    response = api_client.post("/api/auth/login/", MARIA, format="json")

    assert response.status_code == 200
    assert set(response.data) == {"access", "refresh"}


def test_login_email_is_case_insensitive(api_client, sample_data):
    response = api_client.post("/api/auth/login/", {**MARIA, "email": "Maria.Quispe@Example.com"}, format="json")

    assert response.status_code == 200


def test_login_with_a_wrong_password_is_rejected(api_client, sample_data):
    response = api_client.post("/api/auth/login/", {**MARIA, "password": "wrong"}, format="json")

    assert response.status_code == 401


def test_login_validates_the_body(api_client, sample_data):
    response = api_client.post("/api/auth/login/", {"email": MARIA["email"]}, format="json")

    assert response.status_code == 400
    assert "password" in response.data


def test_me_requires_a_token(api_client):
    assert api_client.get("/api/auth/me/").status_code == 401


def test_me_returns_the_profile_without_secrets(api_client, login):
    response = api_client.get("/api/auth/me/", headers=login())

    assert response.json() == {
        "email": "maria.quispe@example.com",
        "full_name": "María Quispe Huamán",
        "dni": "70000001",
    }


def test_refresh_token_gets_a_new_access_token(api_client, sample_data):
    refresh = api_client.post("/api/auth/login/", MARIA, format="json").data["refresh"]

    response = api_client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")

    assert response.status_code == 200
    assert api_client.get("/api/auth/me/", headers=bearer(response.data["access"])).status_code == 200


def test_token_signed_with_another_key_is_rejected(api_client, sample_data):
    forged = pyjwt.encode(
        {"user_id": "1", "token_type": "access"}, "an-attacker-key-that-is-at-least-32-bytes", "HS256"
    )

    assert api_client.get("/api/auth/me/", headers=bearer(forged)).status_code == 401


def test_expired_token_is_rejected(api_client, sample_data):
    token = AccessToken.for_user(User.objects.get(email=MARIA["email"]))
    token.set_exp(lifetime=-timedelta(seconds=1))

    assert api_client.get("/api/auth/me/", headers=bearer(token)).status_code == 401


def test_token_of_a_deleted_user_is_rejected(api_client, sample_data):
    user = User.objects.get(email=MARIA["email"])
    token = AccessToken.for_user(user)
    user.delete()

    assert api_client.get("/api/auth/me/", headers=bearer(token)).status_code == 401
