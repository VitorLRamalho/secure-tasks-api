"""Property-based tests (hypothesis). Born from the DAST findings: the API must never
answer 500, whatever the input."""

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.test_api import _signup_and_login

TITLES = st.text(min_size=1, max_size=120).filter(lambda s: s.strip())
IDS = st.integers(min_value=-(2**70), max_value=2**70)


def fresh_client() -> TestClient:
    """A clean database per generated example (a pytest fixture would be shared)."""
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@settings(max_examples=60, deadline=None)
@given(title=TITLES)
def test_any_valid_title_round_trips(title):
    client = fresh_client()
    user = _signup_and_login(client, "prop@example.com")
    created = client.post("/tasks", json={"title": title}, headers=user)
    assert created.status_code in (201, 422)
    if created.status_code == 201:
        assert created.json()["title"] == title


@settings(max_examples=60, deadline=None)
@given(task_id=IDS)
def test_task_id_never_returns_500(task_id):
    client = fresh_client()
    user = _signup_and_login(client, "prop@example.com")
    response = client.delete(f"/tasks/{task_id}", headers=user)
    assert response.status_code in (404, 422)
