import re

import pytest
from django.contrib.staticfiles import finders


@pytest.mark.django_db
def test_home_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "web/index.html" in [t.name for t in response.templates]
    assert 'id="login-form"' in response.content.decode()


@pytest.mark.django_db
def test_page_only_allows_its_own_scripts(client):
    response = client.get("/")

    assert "default-src 'self'" in response["Content-Security-Policy"]
    # Every <script> must load a file: inline scripts would be blocked by the policy.
    scripts = re.findall(r"<script[^>]*>", response.content.decode())
    assert scripts and all("src=" in tag for tag in scripts)


def test_static_assets_exist():
    for path in ("web/app.js", "web/style.css", "web/favicon.svg"):
        assert finders.find(path), path
