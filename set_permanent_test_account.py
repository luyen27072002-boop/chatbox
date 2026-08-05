from __future__ import annotations

import argparse
import sys

from app import app
from db import set_permanent_test_account


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bật hoặc tắt quyền test không giới hạn cho một tài khoản đã tồn tại."
    )
    parser.add_argument(
        "identifier",
        help="Tên đăng nhập hoặc email của tài khoản đã tạo trên web.",
    )
    parser.add_argument(
        "--disable",
        action="store_true",
        help="Tắt quyền test không giới hạn và đưa tài khoản về quota bình thường.",
    )
    args = parser.parse_args()

    try:
        with app.app_context():
            account = set_permanent_test_account(
                args.identifier,
                enabled=not args.disable,
            )
    except ValueError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1

    state = "ĐÃ TẮT" if args.disable else "ĐÃ BẬT"
    print(f"{state} quyền test không giới hạn.")
    print(f"Tên đăng nhập: {account.get('username', '')}")
    print(f"Email: {account.get('email', '')}")
    print(f"Permanent test: {bool(account.get('permanent_test'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
