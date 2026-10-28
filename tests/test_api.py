PASSWORD = "correct-horse-battery-staple"


def _signup_and_login(client, email: str, password: str = PASSWORD) -> dict[str, str]:
    assert (
        client.post("/auth/register", json={"email": email, "password": password}).status_code
        == 201
    )
    response = client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_security_headers_present(client):
    headers = client.get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in headers["content-security-policy"]
    assert headers["cache-control"] == "no-store"
    assert headers["cross-origin-resource-policy"] == "same-origin"


def test_docs_disabled_outside_dev(client):
    assert client.get("/docs").status_code == 404


def test_weak_password_is_rejected(client):
    response = client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert response.status_code == 422


def test_duplicate_email_is_rejected(client):
    _signup_and_login(client, "dup@example.com")
    response = client.post(
        "/auth/register", json={"email": "dup@example.com", "password": PASSWORD}
    )
    assert response.status_code == 409


def test_wrong_password_and_unknown_email_look_identical(client):
    """Anti-enumeração: a resposta não pode revelar se o e-mail existe."""
    _signup_and_login(client, "vitor@example.com")
    wrong_pw = client.post(
        "/auth/login", data={"username": "vitor@example.com", "password": "wrong-password-123"}
    )
    unknown = client.post(
        "/auth/login", data={"username": "ghost@example.com", "password": "wrong-password-123"}
    )
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_tasks_require_authentication(client):
    assert client.get("/tasks").status_code == 401
    assert (
        client.get("/tasks", headers={"Authorization": "Bearer not-a-real-token"}).status_code
        == 401
    )


def test_task_crud_for_owner(client):
    vitor = _signup_and_login(client, "vitor@example.com")
    created = client.post("/tasks", json={"title": "Estudar Semgrep"}, headers=vitor)
    assert created.status_code == 201
    task_id = created.json()["id"]

    updated = client.put(
        f"/tasks/{task_id}", json={"title": "Estudar Semgrep", "done": True}, headers=vitor
    )
    assert updated.json()["done"] is True
    assert client.delete(f"/tasks/{task_id}", headers=vitor).status_code == 204
    assert client.get("/tasks", headers=vitor).json() == []


def test_user_cannot_access_another_users_task(client):
    """IDOR / OWASP API1 (Broken Object Level Authorization)."""
    vitor = _signup_and_login(client, "vitor@example.com")
    bob = _signup_and_login(client, "bob@example.com")
    task_id = client.post("/tasks", json={"title": "Segredo do Vitor"}, headers=vitor).json()["id"]

    assert (
        client.put(f"/tasks/{task_id}", json={"title": "hackeado"}, headers=bob).status_code == 404
    )
    assert client.delete(f"/tasks/{task_id}", headers=bob).status_code == 404
    assert client.get("/tasks", headers=bob).json() == []
    assert client.get("/tasks", headers=vitor).json()[0]["title"] == "Segredo do Vitor"


def test_password_over_72_bytes_is_rejected(client):
    """O limite do bcrypt é em bytes: 40 caracteres acentuados passam de 72 bytes."""
    long_pw = "ç" * 40  # 80 bytes em UTF-8, mas só 40 caracteres
    r = client.post("/auth/register", json={"email": "long@example.com", "password": long_pw})
    assert r.status_code == 422

    _signup_and_login(client, "ok@example.com")
    r = client.post("/auth/login", data={"username": "ok@example.com", "password": long_pw})
    assert r.status_code == 401  # tratado como credencial inválida, nunca erro 500


def test_task_id_out_of_range_is_422(client):
    """Encontrado pelo DAST: id acima de 64 bits estourava no SQLite e virava 500."""
    vitor = _signup_and_login(client, "vitor@example.com")
    assert client.delete("/tasks/99999999999999999999", headers=vitor).status_code == 422
    assert client.delete("/tasks/0", headers=vitor).status_code == 422


def test_update_of_task_deleted_concurrently_is_404(client, monkeypatch):
    """Encontrado pelo DAST: DELETE e PUT simultâneos no mesmo id viravam 500 (StaleDataError)."""
    from sqlalchemy.orm import Session
    from sqlalchemy.orm.exc import StaleDataError

    ana = _signup_and_login(client, "ana@example.com")
    task_id = client.post("/tasks", json={"title": "corrida"}, headers=ana).json()["id"]

    def commit_after_concurrent_delete(self):
        raise StaleDataError("UPDATE expected 1 row, 0 matched")

    monkeypatch.setattr(Session, "commit", commit_after_concurrent_delete)
    response = client.put(f"/tasks/{task_id}", json={"title": "x"}, headers=ana)
    assert response.status_code == 404
