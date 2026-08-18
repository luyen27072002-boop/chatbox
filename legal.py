from __future__ import annotations

from flask import Blueprint, Flask, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash

from db import anonymize_delete_account, export_user_data, get_account, get_account_for_login
from security_baseline import log_security_event

bp = Blueprint("legal", __name__)


def _user_id() -> str | None:
    value = str(session.get("account_id", "") or "").strip()
    return value or None


def register_legal(app: Flask) -> None:
    app.register_blueprint(bp)


@bp.get("/privacy")
def privacy_page():
    return render_template("legal/privacy.html")


@bp.get("/terms")
def terms_page():
    return render_template("legal/terms.html")


@bp.get("/account/privacy")
def account_privacy_page():
    user_id = _user_id()
    if not user_id or not get_account(user_id):
        return redirect("/")
    return render_template("legal/account_privacy.html", account=get_account(user_id))


@bp.get("/api/account/export")
def account_export():
    user_id = _user_id()
    if not user_id or not get_account(user_id):
        return jsonify({"error": "Bạn cần đăng nhập trước.", "code": "auth_required"}), 401
    return jsonify(export_user_data(user_id))


@bp.delete("/api/account")
def delete_account():
    user_id = _user_id()
    if not user_id:
        return jsonify({"error": "Bạn cần đăng nhập trước.", "code": "auth_required"}), 401
    account = get_account(user_id)
    if not account:
        session.clear()
        return jsonify({"error": "Tài khoản không còn tồn tại.", "code": "not_found"}), 404

    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))
    confirm = str(payload.get("confirm", "")).strip().upper()
    if confirm != "DELETE":
        return jsonify({"error": "Hãy nhập DELETE để xác nhận.", "code": "confirmation_required"}), 400

    secret_row = get_account_for_login(str(account.get("username", "")))
    if not secret_row or not check_password_hash(str(secret_row.get("password_hash", "")), password):
        log_security_event("account_delete_bad_password")
        return jsonify({"error": "Mật khẩu chưa đúng.", "code": "invalid_password"}), 401

    anonymize_delete_account(user_id)
    session.clear()
    log_security_event("account_deleted", level=20)
    return jsonify({"ok": True})
