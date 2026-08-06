from __future__ import annotations

import uuid


def register(client, prefix: str = "lang"):
    suffix = uuid.uuid4().hex[:10]
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "Người học",
            "username": f"{prefix}_{suffix}",
            "email": f"{prefix}_{suffix}@example.com",
            "password": "12345678",
            "remember": True,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["account"]


def start_scene(client, scene_id: str = "coffee-chaos"):
    response = client.post(
        "/api/language/start",
        json={
            "scene_id": scene_id,
            "level": "A1-A2",
            "humor": "chaotic-meme",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_language_pages_require_login(client):
    assert client.get("/language").status_code == 302
    response = client.get("/api/language/overview")
    assert response.status_code == 401
    assert response.get_json()["code"] == "auth_required"


def test_platform_home_and_life_hub_are_separate(client):
    register(client)
    home = client.get("/home")
    assert home.status_code == 200
    assert "Ngoại ngữ cho sinh viên" in home.get_data(as_text=True)
    assert "CV và luyện phỏng vấn" in home.get_data(as_text=True)

    language = client.get("/language")
    assert language.status_code == 200
    assert "Ngoại ngữ nhập vai" in language.get_data(as_text=True)

    life = client.get("/life-space")
    assert life.status_code == 200
    assert "Viết lại hôm nay" in life.get_data(as_text=True)
    assert client.get("/life").location.endswith("/life-space")


def test_language_session_is_persisted_and_uses_shared_quota(client):
    register(client)
    started = start_scene(client)
    session_id = started["session_id"]

    detail = client.get(f"/api/language/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.get_json()["messages"][0]["role"] == "npc"

    response = client.post(
        "/api/language/respond",
        json={
            "session_id": session_id,
            "message": "Can I get a small coffee, please?",
        },
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["quota_source"] == "daily_free"
    assert data["used_total"] == 1
    assert data["score"] > 50
    assert data["progress"] > 0

    saved = client.get(f"/api/language/sessions/{session_id}").get_json()
    assert [item["role"] for item in saved["messages"]] == ["npc", "player", "npc"]
    assert saved["session"]["score"] == data["score"]
    assert saved["session"]["progress"] == data["progress"]

    shared = client.post("/api/session", json={}).get_json()
    assert shared["used_total"] == 1
    assert shared["quota"]["daily_used"] == 1


def test_language_session_cannot_be_read_by_another_account(app):
    owner = app.test_client()
    register(owner, "owner")
    session_id = start_scene(owner)["session_id"]

    stranger = app.test_client()
    register(stranger, "stranger")
    response = stranger.get(f"/api/language/sessions/{session_id}")
    assert response.status_code == 404


def test_delete_data_clears_language_progress_but_not_quota(client):
    register(client)
    session_id = start_scene(client)["session_id"]
    used = client.post(
        "/api/language/respond",
        json={"session_id": session_id, "message": "Can I get coffee, please?"},
    )
    assert used.status_code == 200

    deleted = client.delete("/api/data")
    assert deleted.status_code == 200
    overview = client.get("/api/language/overview").get_json()
    assert overview["sessions"] == []

    quota = client.post("/api/session", json={}).get_json()["quota"]
    assert quota["daily_used"] == 1
