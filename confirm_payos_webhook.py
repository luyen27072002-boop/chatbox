from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from payment_service import PayOSPaymentService, PaymentServiceError


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not public_base_url.startswith("https://"):
        print("PUBLIC_BASE_URL phải là tên miền HTTPS công khai trước khi đăng ký webhook.")
        return 1

    service = PayOSPaymentService(
        client_id=os.getenv("PAYOS_CLIENT_ID", ""),
        api_key=os.getenv("PAYOS_API_KEY", ""),
        checksum_key=os.getenv("PAYOS_CHECKSUM_KEY", ""),
    )
    webhook_url = f"{public_base_url}/api/billing/webhook/payos"
    try:
        service.confirm_webhook(webhook_url)
    except PaymentServiceError as exc:
        print(f"Đăng ký webhook thất bại: {exc}")
        return 1

    print(f"Đã đăng ký webhook payOS: {webhook_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
