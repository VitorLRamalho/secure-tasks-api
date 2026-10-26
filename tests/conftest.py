import os

# Deve vir ANTES de qualquer import de `app`
os.environ["APP_ENV"] = "production"
os.environ["APP_JWT_SECRET"] = "test-only-secret-with-at-least-32-characters"
os.environ["APP_DATABASE_URL"] = "sqlite:///./test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client
