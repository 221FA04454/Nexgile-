from tests.conftest import auth_header, make_client


def test_login_success():
    client = make_client()
    res = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": "demo123"})
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["role"] == "CLIENT"
    assert body["access_token"]
    assert body["refresh_token"]
    assert "error" not in body


def test_login_rejected():
    client = make_client()
    res = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_or_garbage_token():
    client = make_client()
    res = client.get("/api/dashboard", headers={"Authorization": "Bearer not-a-token"})
    assert res.status_code == 401


def test_refresh_and_logout():
    client = make_client()
    login = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": "demo123"})
    token = login.json()["access_token"]
    refresh = login.json()["refresh_token"]
    res = client.post("/api/auth/refresh", headers={"x-refresh-token": refresh})
    assert res.status_code == 200
    new_access = res.json()["access_token"]
    assert new_access
    out = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {new_access}"})
    assert out.status_code == 200
    reused = client.post("/api/auth/refresh", headers={"x-refresh-token": refresh})
    assert reused.status_code == 401
