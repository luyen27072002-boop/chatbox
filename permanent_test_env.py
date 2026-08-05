from __future__ import annotations

import os
import re

from flask import session

from app import app
from db import get_account, set_permanent_test_account


def _configured_permanent_test_emails() -> set[str]:
    """Đọc danh sách email chủ từ biến môi trường.

    Hỗ trợ ngăn cách bằng dấu phẩy, dấu chấm phẩy hoặc xuống dòng.
    So sánh không phân biệt chữ hoa/chữ thường.
    """
    raw = str(os.getenv("PERMANENT_TEST_EMAILS", "") or "")
    return {
        item.strip().lower()
        for item in re.split(r"[,;\n\r]+", raw)
        if item.strip()
    }


@app.before_request
def sync_permanent_test_account_from_environment():
    """Tự bật quyền test vĩnh viễn cho tài khoản có email nằm trong env.

    Hook chạy trước mỗi request đã đăng nhập. Vì vậy quyền được khôi phục sau
    khi Render restart/redeploy mà không cần mở Shell hay sửa SQLite thủ công.
    """
    configured_emails = _configured_permanent_test_emails()
    if not configured_emails:
        return None

    user_id = str(session.get("account_id", "") or "").strip()
    if not user_id:
        return None

    account = get_account(user_id)
    if not account:
        return None

    email = str(account.get("email", "") or "").strip().lower()
    if email not in configured_emails or bool(account.get("permanent_test")):
        return None

    set_permanent_test_account(email, enabled=True)
    return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
