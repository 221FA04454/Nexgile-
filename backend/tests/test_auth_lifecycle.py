from datetime import timedelta

from app.core.security import utcnow
from app.db.session import SessionLocal
from app.models import entities as m
from tests.conftest import auth_header, make_client


STRONG = "SecurePass1!"


def test_signup_success_and_verify_then_login():
    client = make_client()
    res = client.post(
        "/api/auth/signup",
        json={
            "first_name": "Riya",
            "last_name": "Mehta",
            "email": "riya.mehta@example.com",
            "password": STRONG,
            "confirm_password": STRONG,
            "phone": "9876543210",
            "accept_terms": True,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "pending_verification"
    assert "access_token" not in body
    assert body["user"]["email_verified"] is False
    token = body["development"]["verification_url"].split("token=")[1]
    otp = body["development"]["otp"]
    assert len(otp) == 6
    denied = client.post("/api/auth/login", json={"email": "riya.mehta@example.com", "password": STRONG})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "EMAIL_UNVERIFIED"
    verified = client.post("/api/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    login = client.post("/api/auth/login", json={"email": "riya.mehta@example.com", "password": STRONG})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "CLIENT"
    dash = client.get("/api/dashboard", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert dash.status_code == 200


def test_duplicate_signup():
    client = make_client()
    payload = {
        "first_name": "Alex",
        "last_name": "Morgan",
        "email": "alex.morgan@nexgile.demo",
        "password": STRONG,
        "confirm_password": STRONG,
        "accept_terms": True,
    }
    res = client.post("/api/auth/signup", json=payload)
    assert res.status_code == 409


def test_weak_password_and_mismatch():
    client = make_client()
    weak = client.post(
        "/api/auth/signup",
        json={
            "first_name": "A",
            "last_name": "B",
            "email": "weak@example.com",
            "password": "short",
            "confirm_password": "short",
            "accept_terms": True,
        },
    )
    assert weak.status_code == 422
    mismatch = client.post(
        "/api/auth/signup",
        json={
            "first_name": "A",
            "last_name": "B",
            "email": "mismatch@example.com",
            "password": STRONG,
            "confirm_password": "SecurePass2!",
            "accept_terms": True,
        },
    )
    assert mismatch.status_code == 422


def test_incorrect_password_and_lockout():
    client = make_client()
    for _ in range(5):
        last = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": "wrong-pass"})
        assert last.status_code == 401
        assert last.json()["error"]["message"] == "Invalid email or password."
    locked = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": "wrong-pass"})
    assert locked.status_code == 401
    assert "temporarily locked" in locked.json()["error"]["message"].lower()


def test_refresh_rotation_and_revoked_refresh():
    client = make_client()
    login = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": "demo123"})
    first_refresh = login.json()["refresh_token"]
    rotated = client.post("/api/auth/refresh", headers={"x-refresh-token": first_refresh})
    assert rotated.status_code == 200
    client.cookies.clear()
    reused = client.post("/api/auth/refresh", headers={"x-refresh-token": first_refresh})
    assert reused.status_code == 401
    second = rotated.json()["refresh_token"]
    client.cookies.clear()
    out = client.post(
        "/api/auth/logout",
        headers={"x-refresh-token": second, "Authorization": f"Bearer {rotated.json()['access_token']}"},
    )
    assert out.status_code == 200
    client.cookies.clear()
    after = client.post("/api/auth/refresh", headers={"x-refresh-token": second})
    assert after.status_code == 401


def test_forgot_and_reset_password():
    client = make_client()
    asked = client.post("/api/auth/forgot-password", json={"email": "alex.morgan@nexgile.demo"})
    assert asked.status_code == 200
    assert "If an account exists" in asked.json()["message"]
    token = asked.json()["development"]["reset_url"].split("token=")[1]
    reset = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": STRONG, "confirm_password": STRONG},
    )
    assert reset.status_code == 200
    old = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": "demo123"})
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"email": "alex.morgan@nexgile.demo", "password": STRONG})
    assert new.status_code == 200
    reused = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "AnotherPass1!", "confirm_password": "AnotherPass1!"},
    )
    assert reused.status_code == 401


def test_unknown_email_does_not_enumerate():
    client = make_client()
    missing = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert missing.status_code == 200
    known = client.post("/api/auth/forgot-password", json={"email": "alex.morgan@nexgile.demo"})
    assert missing.json()["message"] == known.json()["message"]
    assert "development" not in missing.json()


def test_expired_verification_token():
    client = make_client()
    signup = client.post(
        "/api/auth/signup",
        json={
            "first_name": "Dev",
            "last_name": "User",
            "email": "dev.user@example.com",
            "password": STRONG,
            "confirm_password": STRONG,
            "accept_terms": True,
        },
    )
    token = signup.json()["development"]["verification_url"].split("token=")[1]
    db = SessionLocal()
    try:
        row = db.query(m.AuthToken).filter(m.AuthToken.purpose == "email_verify").order_by(m.AuthToken.id.desc()).first()
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.add(row)
        db.commit()
    finally:
        db.close()
    res = client.post("/api/auth/verify-email", json={"token": token})
    assert res.status_code == 401


def test_resend_verification_and_otp():
    client = make_client()
    client.post(
        "/api/auth/signup",
        json={
            "first_name": "Otp",
            "last_name": "User",
            "email": "otp.user@example.com",
            "password": STRONG,
            "confirm_password": STRONG,
            "accept_terms": True,
        },
    )
    resend = client.post("/api/auth/resend-verification", json={"email": "otp.user@example.com"})
    assert resend.status_code == 200
    otp = resend.json()["development"]["otp"]
    verified = client.post("/api/auth/verify-email", json={"otp": otp})
    assert verified.status_code == 200


def test_sessions_endpoint_requires_auth():
    client = make_client()
    assert client.get("/api/auth/sessions").status_code == 401
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    res = client.get("/api/auth/sessions", headers=headers)
    assert res.status_code == 200
    assert res.json()["sessions"]


def test_public_config_exposes_password_policy_not_secrets():
    client = make_client()
    body = client.get("/api/auth/public-config").json()
    assert body["password_policy"]["min_length"] == 10
    blob = str(body).lower()
    assert "jwt" not in blob
    assert "groq" not in blob
