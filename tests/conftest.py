from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from types import SimpleNamespace

from app import create_app


class FakeAIService:
    model = "test-stub"
    is_configured = True

    def moderate(self, text: str):
        return SimpleNamespace(
            requires_urgent_support=False,
            must_block=False,
            categories={},
        )

    def generate_reply(self, **kwargs):
        persona = kwargs.get("response_style", "luyen")
        tone = kwargs.get("tone_style", "gentle")
        mode = kwargs.get("mode", "listen")
        message = kwargs.get("message", "")
        return f"{persona}|{tone}|{mode}: {message[:40]}"

    def refresh_memory(self, old_memory, recent_history):
        return old_memory


class FakePaymentService:
    is_configured = True

    def create_checkout(self, *, order_code, amount, description, return_url, cancel_url, item_name):
        return SimpleNamespace(
            checkout_url=f"https://pay.test/{order_code}",
            payment_link_id=f"plink-{order_code}",
        )

    def verify_webhook(self, raw_body: bytes):
        payload = json.loads(raw_body.decode("utf-8"))
        return SimpleNamespace(
            order_code=int(payload["orderCode"]),
            amount=int(payload["amount"]),
            code=str(payload.get("code", "00")),
        )


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "AI_SERVICE": FakeAIService(),
            "OPENAI_API_KEY": "",
            "FREE_WELCOME_LIMIT": 10,
            "FREE_DAILY_LIMIT": 3,
            "MEMORY_REFRESH_EVERY": 0,
            "STORE_CHAT_HISTORY": True,
            "SECRET_KEY": "test-secret",
            "PAYMENT_SERVICE": FakePaymentService(),
            "PUBLIC_BASE_URL": "http://localhost",
            "PAYMENT_ALLOW_LOCALHOST": True,
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()
