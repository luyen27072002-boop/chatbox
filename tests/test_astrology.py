from __future__ import annotations

import uuid

import pytest

import astrology_service
from astrology_service import calculate_birth_profile
from tuvi_engine import birth_hour_index


def _fake_full_chart(**kwargs):
    names = ["Mệnh", "Phụ Mẫu", "Phúc Đức", "Điền Trạch", "Quan Lộc", "Nô Bộc", "Thiên Di", "Tật Ách", "Tài Bạch", "Tử Tức", "Phu Thê", "Huynh Đệ"]
    branches = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]
    grids = {1:"g11",2:"g10",3:"g9",4:"g7",5:"g5",6:"g1",7:"g2",8:"g3",9:"g4",10:"g6",11:"g8",12:"g12"}
    palaces=[]
    for i in range(1,13):
        major={"name":"Tử Vi" if i==1 else "Thiên Phủ","element":"Thổ","quality":"M","type":1,"major":True}
        minor={"name":"Tả Phù","element":"Mộc","quality":"","type":5,"major":False}
        palaces.append({"number":i,"grid":grids[i],"name":names[i-1],"can_chi":f"Can {branches[i-1]}","branch":branches[i-1],"element":"Mộc","yin_yang":"Dương","is_than":i==2,"dai_han":3+(i-1)*10,"tieu_han":i,"tuan":i==3,"triet":i==4,"stars":[major,minor],"major_stars":[major],"minor_stars":[minor]})
    return {"available":True,"engine":"ansaotuvi","engine_version":"0.1.28","system":"Tử Vi Đẩu Số","time_zone":7,"birth_hour_index":6,"birth_hour_branch":"Tỵ","heaven":{"name":kwargs.get("display_name") or "Tester","gender":"Nữ","solar_day":15,"solar_month":6,"solar_year":2000,"lunar_day":14,"lunar_month":5,"lunar_year":2000,"bureau_name":"Thổ Ngũ Cục","menh_chu":"Liêm Trinh","than_chu":"Văn Xương","destiny":"Bạch Lạp Kim"},"palaces":palaces,"cycle":{"current_age":26,"current_year":2026,"current_year_can_chi":"Bính Ngọ","decade_palace":{"name":"Phúc Đức","dai_han":23,"major_stars":["Thiên Phủ"]}}}


@pytest.fixture(autouse=True)
def fake_tuvi_engine(monkeypatch):
    monkeypatch.setattr(astrology_service, "build_full_tuvi_chart", _fake_full_chart)


def register(client, prefix: str = "astro"):
    suffix = uuid.uuid4().hex[:10]
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "Người xem tử vi",
            "username": f"{prefix}_{suffix}",
            "email": f"{prefix}_{suffix}@example.com",
            "password": "12345678",
            "remember": True,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["account"]


def test_hour_mapping_for_tuvi_engine():
    assert birth_hour_index(23) == 1
    assert birth_hour_index(0) == 1
    assert birth_hour_index(1) == 2
    assert birth_hour_index(10) == 6
    assert birth_hour_index(21) == 12


def test_birth_profile_calculation_is_deterministic():
    profile = calculate_birth_profile(
        birth_date="2000-06-15",
        birth_time="10:30",
        birth_place="Hà Nội",
        gender="female",
        display_name="Tester",
    )
    assert profile["can_chi_year"] == "Canh Thìn"
    assert profile["zodiac_animal"] == "Rồng"
    assert profile["nap_am"] == "Bạch Lạp Kim"
    assert profile["nap_am_element"] == "Kim"
    assert profile["birth_hour_branch"] == "Tỵ"
    assert profile["tuvi_chart"]["available"] is True
    assert len(profile["tuvi_chart"]["palaces"]) == 12
    assert profile["tuvi_chart"]["palaces"][0]["major_stars"][0]["name"] == "Tử Vi"


def test_full_chart_requires_birth_time_and_gender():
    with pytest.raises(astrology_service.AstrologyServiceError):
        calculate_birth_profile(birth_date="2000-06-15", birth_time="", gender="female")
    with pytest.raises(astrology_service.AstrologyServiceError):
        calculate_birth_profile(birth_date="2000-06-15", birth_time="10:30", gender="")


def test_astrology_requires_login(client):
    assert client.get("/astrology").status_code == 302
    response = client.get("/api/astrology/overview")
    assert response.status_code == 401
    assert response.get_json()["code"] == "auth_required"


def test_astrology_page_renders_after_login(client):
    register(client)
    page = client.get("/astrology")
    assert page.status_code == 200
    text = page.get_data(as_text=True)
    assert "Tử vi &amp; Lá số" in text or "Tử vi & Lá số" in text
    assert "traditionalChart" in text
    assert "birthTime" in text


def test_create_reading_persists_full_chart_and_uses_shared_quota(client):
    register(client)
    created = client.post(
        "/api/astrology/chart",
        json={
            "birth_date": "2000-06-15",
            "birth_time": "10:30",
            "birth_place": "Hà Nội",
            "gender": "female",
            "ui_language": "vi",
        },
    )
    assert created.status_code == 201, created.get_json()
    data = created.get_json()
    profile=data["reading"]["profile"]
    assert profile["can_chi_year"] == "Canh Thìn"
    assert profile["tuvi_chart"]["engine"] == "ansaotuvi"
    assert len(profile["tuvi_chart"]["palaces"]) == 12
    assert data["reading"]["reading"]["near_future"]["areas"]
    assert data["quota_source"] == "daily_free"

    overview = client.get("/api/astrology/overview")
    assert overview.status_code == 200
    saved = overview.get_json()["reading"]
    assert saved["id"] == data["reading"]["id"]
    assert saved["profile"]["tuvi_chart"]["palaces"][0]["name"] == "Mệnh"

    shared = client.post("/api/session", json={}).get_json()
    assert shared["used_total"] == 1
    assert shared["quota"]["daily_used"] == 1


def test_followup_question_uses_same_reading_and_one_more_quota(client):
    register(client)
    created = client.post(
        "/api/astrology/chart",
        json={"birth_date":"1999-10-20","birth_time":"22:10","gender":"male","ui_language":"vi"},
    ).get_json()
    reading_id = created["reading"]["id"]

    asked = client.post(
        "/api/astrology/ask",
        json={
            "reading_id": reading_id,
            "question": "Phân tích kỹ cung Quan Lộc của tôi.",
            "ui_language": "vi",
        },
    )
    assert asked.status_code == 200, asked.get_json()
    payload = asked.get_json()
    assert payload["reading_id"] == reading_id
    assert payload["answer"]["answer"]

    overview = client.get("/api/astrology/overview").get_json()
    assert [item["role"] for item in overview["messages"]] == ["user", "assistant"]
    shared = client.post("/api/session", json={}).get_json()
    assert shared["used_total"] == 2


def test_delete_data_clears_astrology_but_keeps_quota(client):
    register(client)
    response = client.post(
        "/api/astrology/chart",
        json={"birth_date":"2001-01-01","birth_time":"06:30","gender":"female","ui_language":"vi"},
    )
    assert response.status_code == 201
    deleted = client.delete("/api/data")
    assert deleted.status_code == 200
    overview = client.get("/api/astrology/overview").get_json()
    assert overview["reading"] is None
    quota = client.post("/api/session", json={}).get_json()["quota"]
    assert quota["daily_used"] == 1
