from __future__ import annotations

import json
import uuid

import career


def test_job_match_prefers_matching_role_and_skill():
    profile = {
        "desired_role": "Robotics Engineer",
        "location": "Remote",
        "work_type": "full_time",
        "skills": ["Python", "ROS2", "YOLO"],
    }
    good = {
        "title": "Robotics Engineer",
        "description": "Build ROS2 robotics systems using Python and YOLO.",
        "location": "Worldwide",
        "job_type": "full_time",
    }
    weak = {
        "title": "Accountant",
        "description": "Accounting, tax and financial reporting.",
        "location": "New York",
        "job_type": "full_time",
    }
    assert career._match_job(profile, good)["score"] > career._match_job(profile, weak)["score"]


def test_safe_url_rejects_non_http():
    assert career._safe_url("javascript:alert(1)") == ""
    assert career._safe_url("file:///etc/passwd") == ""
    assert career._safe_url("https://example.com/jobs/1").startswith("https://")


def test_career_routes_require_auth(client):
    assert client.get("/api/career/overview").status_code == 401
    assert client.get("/api/career/jobs/search").status_code == 401


def test_saved_job_is_scoped_to_owner(client):
    def register(prefix):
        suffix = uuid.uuid4().hex[:8]
        r = client.post("/api/auth/register", json={
            "display_name": "Career Test",
            "username": f"{prefix}_{suffix}",
            "email": f"{prefix}_{suffix}@example.com",
            "password": "12345678",
            "remember": True,
            "accept_terms": True,
            "accept_privacy": True,
            "accept_ai": True,
        })
        assert r.status_code == 201
        return r.get_json()["account"]["id"]

    user_a = register("career_a")
    created = client.post("/api/career/jobs/save", json={"job":{
        "title":"Robotics Engineer","company":"Example","description":"Python ROS2 robotics"
    }})
    assert created.status_code == 201
    job_id = created.get_json()["id"]
    client.post("/api/auth/logout", json={})

    register("career_b")
    blocked = client.delete(f"/api/career/jobs/saved/{job_id}")
    assert blocked.status_code == 404
