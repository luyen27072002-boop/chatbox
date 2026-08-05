from __future__ import annotations

import uuid


def register(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "Người test",
            "username": f"test_{suffix}",
            "email": f"{suffix}@example.com",
            "password": "12345678",
            "remember": True,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["account"]


def chat_payload(**overrides):
    payload = {
        "message": "Tao biết nhắn lại chỉ mệt mà vẫn cứ muốn nhắn.",
        "mode": "listen",
        "category": "love",
        "pronoun_style": "tao_may",
        "response_style": "luyen",
        "tone_style": "gentle",
        "language": "vi",
        "conversation_id": "",
    }
    payload.update(overrides)
    return payload


def test_health_reports_dataset_engine(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["profile_engine"] == "v2"
    assert data["conversation_engine"] == "v5-billing-payos"


def test_session_requires_login(client):
    response = client.post("/api/session")
    assert response.status_code == 401
    assert response.get_json()["code"] == "auth_required"


def test_tone_and_persona_settings_are_persisted(client):
    register(client)
    response = client.post(
        "/api/settings",
        json={
            "pronoun_style": "tao_may",
            "response_style": "strict",
            "tone_style": "realistic",
            "language": "vi",
        },
    )
    assert response.status_code == 200
    user = response.get_json()["user"]
    assert user["pronoun_style"] == "tao_may"
    assert user["tone_style"] == "realistic"
    assert user["response_style"] == "strict"


def test_gentle_and_realistic_replies_are_different(client):
    register(client)
    gentle = client.post(
        "/api/chat",
        json=chat_payload(tone_style="gentle"),
    )
    realistic = client.post(
        "/api/chat",
        json=chat_payload(tone_style="realistic"),
    )
    assert gentle.status_code == 200, gentle.get_json()
    assert realistic.status_code == 200, realistic.get_json()
    gentle_data = gentle.get_json()
    realistic_data = realistic.get_json()
    assert gentle_data["tone_style"] == "gentle"
    assert realistic_data["tone_style"] == "realistic"
    assert gentle_data["response_style"] == "luyen"
    assert realistic_data["response_style"] == "luyen"
    assert gentle_data["reply"] != realistic_data["reply"]


def test_all_personas_can_be_selected(client):
    register(client)
    replies = {}
    for persona in [
        "adaptive", "strict", "gentle", "rational",
        "practical", "light_humor", "luyen",
    ]:
        response = client.post(
            "/api/chat",
            json=chat_payload(
                message="Người ta trả lời chậm nên tao nghĩ chắc họ chán tao rồi.",
                mode="clarify",
                response_style=persona,
                tone_style="realistic",
            ),
        )
        assert response.status_code == 200, response.get_json()
        data = response.get_json()
        assert data["response_style"] == persona
        replies[persona] = data["reply"]
    assert len(set(replies.values())) >= 5


def test_explicit_request_changes_mode(client):
    register(client)
    first = client.post("/api/chat", json=chat_payload(message="Tao muốn kể chuyện này.")).get_json()
    conversation_id = first["conversation_id"]

    clarify = client.post(
        "/api/chat",
        json=chat_payload(
            message="Thế mày phân tích đi.",
            mode="listen",
            conversation_id=conversation_id,
        ),
    )
    assert clarify.status_code == 200
    assert clarify.get_json()["mode"] == "clarify"

    advice = client.post(
        "/api/chat",
        json=chat_payload(
            message="Giờ cho tao lời khuyên đi.",
            mode="clarify",
            conversation_id=conversation_id,
        ),
    )
    assert advice.status_code == 200
    assert advice.get_json()["mode"] == "advice"


def test_history_keeps_tone_and_mode(client):
    register(client)
    response = client.post(
        "/api/chat",
        json=chat_payload(tone_style="realistic", mode="clarify", response_style="rational"),
    )
    assert response.status_code == 200
    conversation_id = response.get_json()["conversation_id"]
    detail = client.get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    messages = detail.get_json()["messages"]
    assert [row["role"] for row in messages] == ["user", "assistant"]
    assert all(row["tone_style"] == "realistic" for row in messages)
    assert all(row["mode"] == "clarify" for row in messages)
    assert all(row["response_style"] == "rational" for row in messages)


def test_invalid_tone_is_rejected(client):
    register(client)
    response = client.post(
        "/api/chat",
        json=chat_payload(tone_style="insulting"),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Cách nói không hợp lệ."


def test_invalid_persona_is_rejected(client):
    register(client)
    response = client.post(
        "/api/chat",
        json=chat_payload(response_style="mang_nguoi_dung"),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Tính cách phản hồi không hợp lệ."


def test_welcome_and_daily_free_quota(client):
    register(client)
    expected_sources = ["daily_free"] * 3 + ["welcome"] * 10
    for index, expected_source in enumerate(expected_sources):
        response = client.post(
            "/api/chat",
            json=chat_payload(message=f"Tin nhắn miễn phí số {index + 1}"),
        )
        assert response.status_code == 200, response.get_json()
        data = response.get_json()
        assert data["used_total"] == index + 1
        assert data["free_limit"] == 10
        assert data["quota_source"] == expected_source

    blocked = client.post(
        "/api/chat",
        json=chat_payload(message="Tin nhắn thứ mười bốn"),
    )
    assert blocked.status_code == 429
    blocked_data = blocked.get_json()
    assert blocked_data["code"] == "quota_exhausted"
    assert blocked_data["quota"]["daily_remaining"] == 0
    assert blocked_data["quota"]["welcome_remaining"] == 0


def test_deleting_chat_data_does_not_reset_free_quota(client):
    register(client)
    response = client.post("/api/chat", json=chat_payload(message="Dùng một lượt"))
    assert response.status_code == 200
    assert response.get_json()["used_total"] == 1
    assert response.get_json()["quota_source"] == "daily_free"

    deleted = client.delete("/api/data")
    assert deleted.status_code == 200

    session_data = client.post("/api/session").get_json()
    assert session_data["used_total"] == 1
    assert session_data["free_limit"] == 10
    assert session_data["quota"]["daily_used"] == 1
    assert session_data["quota"]["daily_remaining"] == 2


def test_pricing_catalog_has_rounded_topups_and_monthly_plans(client):
    register(client)
    response = client.get("/api/billing/plans")
    assert response.status_code == 200
    data = response.get_json()
    topups = data["plans"]["topups"]
    monthly = data["plans"]["monthly"]
    assert [(item["price_vnd"], item["credits"]) for item in topups] == [
        (5000, 25),
        (10000, 55),
        (20000, 120),
        (50000, 320),
        (100000, 700),
        (200000, 1500),
        (500000, 4000),
    ]
    assert [item["price_vnd"] for item in monthly] == [
        49000, 99000, 199000, 399000, 799000
    ]
    unlimited = monthly[-1]
    assert unlimited["unlimited"] is True
    assert unlimited["daily_fair_limit"] == 200


def test_topup_payment_is_applied_once(client):
    register(client)
    checkout = client.post("/api/billing/checkout", json={"plan_id": "topup_5k"})
    assert checkout.status_code == 200, checkout.get_json()
    checkout_data = checkout.get_json()
    assert checkout_data["checkout_url"].startswith("https://pay.test/")
    order = checkout_data["order"]

    webhook_payload = {
        "orderCode": order["order_code"],
        "amount": 5000,
        "code": "00",
    }
    first = client.post("/api/billing/webhook/payos", json=webhook_payload)
    assert first.status_code == 200, first.get_json()
    assert first.get_json()["applied"] is True

    status = client.get("/api/billing/status").get_json()
    assert status["quota"]["purchased_credits"] == 25

    duplicate = client.post("/api/billing/webhook/payos", json=webhook_payload)
    assert duplicate.status_code == 200
    assert duplicate.get_json()["applied"] is False
    status_again = client.get("/api/billing/status").get_json()
    assert status_again["quota"]["purchased_credits"] == 25


def test_monthly_and_unlimited_payment_create_subscriptions(client):
    register(client)
    limited_checkout = client.post(
        "/api/billing/checkout", json={"plan_id": "month_49k"}
    ).get_json()
    limited_order = limited_checkout["order"]
    paid = client.post(
        "/api/billing/webhook/payos",
        json={
            "orderCode": limited_order["order_code"],
            "amount": 49000,
            "code": "00",
        },
    )
    assert paid.status_code == 200
    quota = client.get("/api/billing/status").get_json()["quota"]
    assert quota["subscription_remaining"] == 400

    unlimited_checkout = client.post(
        "/api/billing/checkout", json={"plan_id": "month_unlimited_799k"}
    ).get_json()
    unlimited_order = unlimited_checkout["order"]
    paid_unlimited = client.post(
        "/api/billing/webhook/payos",
        json={
            "orderCode": unlimited_order["order_code"],
            "amount": 799000,
            "code": "00",
        },
    )
    assert paid_unlimited.status_code == 200
    quota = client.get("/api/billing/status").get_json()["quota"]
    assert quota["unlimited_active"] is True
    assert quota["unlimited_daily_remaining"] == 200


def test_wrong_webhook_amount_does_not_add_credit(client):
    register(client)
    checkout = client.post("/api/billing/checkout", json={"plan_id": "topup_5k"})
    order = checkout.get_json()["order"]
    response = client.post(
        "/api/billing/webhook/payos",
        json={"orderCode": order["order_code"], "amount": 10000, "code": "00"},
    )
    assert response.status_code == 400
    quota = client.get("/api/billing/status").get_json()["quota"]
    assert quota["purchased_credits"] == 0



def test_verified_unknown_webhook_is_accepted_for_payos_confirmation(client):
    response = client.post(
        "/api/billing/webhook/payos",
        json={"orderCode": 123, "amount": 3000, "code": "00"},
    )
    assert response.status_code == 200
    assert response.get_json()["ignored"] is True
