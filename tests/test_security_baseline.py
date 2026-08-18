from __future__ import annotations

import uuid


def _register(client, prefix: str):
    suffix = uuid.uuid4().hex[:8]
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": prefix,
            "username": f"{prefix}_{suffix}",
            "email": f"{prefix}_{suffix}@example.com",
            "password": "12345678",
            "remember": True,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["account"]


def _login(client, identifier: str, password: str = "12345678"):
    return client.post("/api/auth/login", json={"identifier": identifier, "password": password})


def test_security_headers_are_present(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_cross_origin_mutation_is_blocked(client):
    response = client.post(
        "/api/session",
        headers={"Origin": "https://evil.example"},
        json={},
    )
    assert response.status_code == 403
    assert response.get_json()["code"] == "origin_rejected"


def test_login_rate_limit(client):
    for _ in range(10):
        response = _login(client, "nobody@example.com", "wrong-password")
        assert response.status_code == 401
    response = _login(client, "nobody@example.com", "wrong-password")
    assert response.status_code == 429
    assert response.get_json()["code"] == "rate_limited"
    assert int(response.headers["Retry-After"]) >= 1


def test_user_b_cannot_read_user_a_conversation(client):
    a = _register(client, "ownerA")
    chat = client.post(
        "/api/chat",
        json={
            "message": "Tin riêng của A",
            "mode": "listen",
            "category": "other",
            "pronoun_style": "minh_ban",
            "response_style": "luyen",
            "tone_style": "gentle",
            "language": "vi",
            "conversation_id": "",
        },
    )
    assert chat.status_code == 200, chat.get_json()
    conversation_id = chat.get_json()["conversation"]["id"]
    client.post("/api/auth/logout", json={})

    _register(client, "ownerB")
    forbidden = client.get(f"/api/conversations/{conversation_id}")
    assert forbidden.status_code == 404


def test_user_b_cannot_delete_user_a_finance_transaction(client):
    _register(client, "moneyA")
    created = client.post(
        "/api/finance/transaction",
        json={"kind": "expense", "amount": 50000, "category": "food", "note": "private", "occurred_on": "2026-08-08"},
    )
    assert created.status_code == 201, created.get_json()
    transaction_id = created.get_json()["transaction_id"]
    client.post("/api/auth/logout", json={})

    _register(client, "moneyB")
    response = client.delete(f"/api/finance/transaction/{transaction_id}")
    assert response.status_code == 404
