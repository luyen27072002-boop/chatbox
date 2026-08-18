from __future__ import annotations

import uuid


def _register(client, prefix: str = "privacy"):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "display_name": "Privacy Test",
        "username": f"{prefix}_{suffix}",
        "email": f"{prefix}_{suffix}@example.com",
        "password": "12345678",
        "remember": True,
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["account"], payload


def test_export_includes_new_private_modules(client):
    _register(client)
    tx = client.post(
        "/api/finance/transaction",
        json={"kind": "expense", "amount": 120000, "category": "food", "note": "lunch", "occurred_on": "2026-08-08"},
    )
    assert tx.status_code == 201
    export = client.get("/api/account/export")
    assert export.status_code == 200
    data = export.get_json()
    assert "finance" in data
    assert "self_discovery" in data
    assert "billing" in data
    assert data["finance"]["finance_transactions"]


def test_delete_account_requires_password_and_disables_login(client):
    account, payload = _register(client, "delete")
    bad = client.delete("/api/account", json={"password": "wrong", "confirm": "DELETE"})
    assert bad.status_code == 401

    good = client.delete("/api/account", json={"password": payload["password"], "confirm": "DELETE"})
    assert good.status_code == 200
    assert good.get_json()["ok"] is True

    status = client.get("/api/auth/status")
    assert status.status_code == 200
    assert status.get_json()["authenticated"] is False

    login = client.post(
        "/api/auth/login",
        json={"identifier": payload["username"], "password": payload["password"]},
    )
    assert login.status_code == 401
