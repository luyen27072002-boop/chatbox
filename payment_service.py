from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PaymentServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckoutResult:
    checkout_url: str
    payment_link_id: str


class PayOSPaymentService:
    """Small wrapper around the official payOS SDK.

    Importing payos is delayed until credentials are present so local chat mode
    still runs before payment is configured.
    """

    def __init__(self, *, client_id: str, api_key: str, checksum_key: str):
        self.client_id = client_id.strip()
        self.api_key = api_key.strip()
        self.checksum_key = checksum_key.strip()
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.api_key and self.checksum_key)

    def _get_client(self):
        if not self.is_configured:
            raise PaymentServiceError("payOS chưa được cấu hình trên server.")
        if self._client is not None:
            return self._client
        try:
            from payos import PayOS
        except ImportError as exc:
            raise PaymentServiceError(
                "Server chưa cài thư viện payos. Hãy chạy pip install -r requirements.txt."
            ) from exc
        self._client = PayOS(
            client_id=self.client_id,
            api_key=self.api_key,
            checksum_key=self.checksum_key,
        )
        return self._client

    def create_checkout(
        self,
        *,
        order_code: int,
        amount: int,
        description: str,
        return_url: str,
        cancel_url: str,
        item_name: str,
    ) -> CheckoutResult:
        try:
            from payos.types import CreatePaymentLinkRequest
        except ImportError as exc:
            raise PaymentServiceError(
                "Server chưa cài thư viện payos. Hãy chạy pip install -r requirements.txt."
            ) from exc

        request_data = CreatePaymentLinkRequest(
            order_code=int(order_code),
            amount=int(amount),
            description=str(description)[:25],
            cancel_url=cancel_url,
            return_url=return_url,
        )
        try:
            response = self._get_client().payment_requests.create(
                payment_data=request_data
            )
        except Exception as exc:  # SDK raises typed API errors; keep app boundary stable.
            raise PaymentServiceError(f"Không tạo được link thanh toán: {exc}") from exc

        checkout_url = str(getattr(response, "checkout_url", "") or "")
        payment_link_id = str(getattr(response, "payment_link_id", "") or "")
        if not checkout_url:
            raise PaymentServiceError("payOS không trả về checkout URL.")
        return CheckoutResult(
            checkout_url=checkout_url,
            payment_link_id=payment_link_id,
        )

    def confirm_webhook(self, webhook_url: str) -> Any:
        try:
            return self._get_client().webhooks.confirm(str(webhook_url))
        except Exception as exc:
            raise PaymentServiceError(f"Không đăng ký được webhook payOS: {exc}") from exc

    def verify_webhook(self, raw_body: bytes) -> Any:
        try:
            return self._get_client().webhooks.verify(raw_body)
        except Exception as exc:
            raise PaymentServiceError(f"Webhook payOS không hợp lệ: {exc}") from exc
