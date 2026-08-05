from __future__ import annotations

from test_app import chat_payload, register


def test_urgent_fallback_returns_200_without_calling_model_or_spending_quota(client):
    register(client)
    before = client.post("/api/session").get_json()

    response = client.post(
        "/api/chat",
        json=chat_payload(message="tao không muốn sống nữa"),
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["safety_route"] is True
    assert data["quota_source"] == "safety"
    assert data["used_total"] == before["used_total"]
    assert "nghiêm trọng" in data["reply"].lower()


def test_urgent_fallback_still_works_after_normal_quota_is_exhausted(client):
    register(client)
    for index in range(13):
        response = client.post(
            "/api/chat",
            json=chat_payload(message=f"Tin nhắn thường số {index + 1}"),
        )
        assert response.status_code == 200, response.get_json()

    blocked = client.post(
        "/api/chat",
        json=chat_payload(message="Tin nhắn thường đã hết lượt"),
    )
    assert blocked.status_code == 429

    urgent = client.post(
        "/api/chat",
        json=chat_payload(message="tao không muốn sống nữa"),
    )
    assert urgent.status_code == 200, urgent.get_json()
    data = urgent.get_json()
    assert data["safety_route"] is True
    assert data["quota_source"] == "safety"
    assert data["used_total"] == 13
