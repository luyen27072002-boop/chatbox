from __future__ import annotations

from db import set_permanent_test_account


def _register_owner(client):
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "Chủ dự án",
            "username": "owner_test",
            "email": "owner-test@example.com",
            "password": "12345678",
            "remember": True,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["account"]


def _payload(index: int):
    return {
        "message": f"Tin nhắn test không giới hạn số {index}",
        "mode": "listen",
        "category": "other",
        "pronoun_style": "tao_may",
        "response_style": "luyen",
        "tone_style": "gentle",
        "language": "vi",
        "conversation_id": "",
    }


def test_permanent_test_account_never_uses_paid_or_free_quota(app, client):
    _register_owner(client)
    with app.app_context():
        account = set_permanent_test_account("owner_test", enabled=True)
        assert account["permanent_test"] is True

    for index in range(20):
        response = client.post("/api/chat", json=_payload(index + 1))
        assert response.status_code == 200, response.get_json()
        data = response.get_json()
        assert data["quota_source"] == "permanent_test"
        assert data["quota"]["permanent_test"] is True
        assert data["quota"]["can_chat"] is True

    session_data = client.post("/api/session").get_json()
    quota = session_data["quota"]
    assert quota["permanent_test"] is True
    assert quota["daily_used"] == 0
    assert quota["welcome_used"] == 0
    assert quota["purchased_credits"] == 0
    assert quota["used_total"] == 20


def test_permanent_test_can_be_disabled(app, client):
    _register_owner(client)
    with app.app_context():
        set_permanent_test_account("owner-test@example.com", enabled=True)
        account = set_permanent_test_account("owner_test", enabled=False)
        assert account["permanent_test"] is False

    response = client.post("/api/chat", json=_payload(1))
    assert response.status_code == 200
    assert response.get_json()["quota_source"] == "daily_free"
