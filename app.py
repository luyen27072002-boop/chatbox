from __future__ import annotations

import json
import os
import re
import unicodedata
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, g, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ai_service import AIService, AIServiceError
from billing import PricingCatalog
from payment_service import PayOSPaymentService, PaymentServiceError
from db import (
    clear_user_data,
    count_user_messages,
    create_account,
    create_conversation,
    delete_conversation,
    export_user_data,
    get_account,
    get_account_for_login,
    get_conversation,
    get_conversation_summary,
    get_history,
    get_or_create_user,
    apply_paid_order,
    create_payment_order,
    finalize_message_quota,
    get_payment_order,
    get_quota_status,
    get_usage_total,
    init_app as init_db_app,
    list_conversations,
    list_payment_orders,
    mark_payment_failed,
    refund_message_quota,
    reserve_message_quota,
    update_payment_checkout,
    mark_account_login,
    rename_conversation,
    save_message,
    update_conversation_summary,
    update_user_profile,
    update_user_settings,
)
from profile_engine import profile_schema
from prompting import (
    VALID_CATEGORIES,
    VALID_MODES,
    VALID_PRONOUN_STYLES,
    VALID_RESPONSE_STYLES,
    VALID_TONE_STYLES,
    VALID_LANGUAGES,
)
from safety import urgent_fallback_detected, urgent_support_message
from life_features import register_life_features
from language_game import register_language_game

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{3,24}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-change-me"),
        DATABASE=os.getenv("DATABASE_PATH", str(BASE_DIR / "app.db")),
        BRAND_NAME=os.getenv("PLATFORM_BRAND_NAME", "Mở Lối"),
        BRAND_TAGLINE=os.getenv("PLATFORM_BRAND_TAGLINE", "Học tập · Sự nghiệp · Cuộc sống"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
        FREE_WELCOME_LIMIT=int(os.getenv("FREE_WELCOME_LIMIT", os.getenv("FREE_MESSAGE_LIMIT", "10"))),
        FREE_DAILY_LIMIT=int(os.getenv("FREE_DAILY_LIMIT", "3")),
        MAX_MESSAGE_CHARS=int(os.getenv("MAX_MESSAGE_CHARS", "4000")),
        MEMORY_REFRESH_EVERY=int(os.getenv("MEMORY_REFRESH_EVERY", "6")),
        STORE_CHAT_HISTORY=os.getenv("STORE_CHAT_HISTORY", "true").lower()
        in {"1", "true", "yes"},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower()
        in {"1", "true", "yes"},
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        BILLING_TIMEZONE=os.getenv("BILLING_TIMEZONE", "Asia/Ho_Chi_Minh"),
        PUBLIC_BASE_URL=os.getenv("PUBLIC_BASE_URL", "").rstrip("/"),
        PAYOS_CLIENT_ID=os.getenv("PAYOS_CLIENT_ID", ""),
        PAYOS_API_KEY=os.getenv("PAYOS_API_KEY", ""),
        PAYOS_CHECKSUM_KEY=os.getenv("PAYOS_CHECKSUM_KEY", ""),
        PAYMENT_ALLOW_LOCALHOST=os.getenv("PAYMENT_ALLOW_LOCALHOST", "false").lower() in {"1", "true", "yes"},
        LANGUAGE_MAX_MESSAGE_CHARS=int(os.getenv("LANGUAGE_MAX_MESSAGE_CHARS", "500")),
    )
    if test_config:
        app.config.update(test_config)

    init_db_app(app)
    ai = app.config.get("AI_SERVICE") or AIService(
        api_key=app.config["OPENAI_API_KEY"],
        model=app.config["OPENAI_MODEL"],
        base_dir=BASE_DIR,
    )
    pricing = app.config.get("PRICING_CATALOG") or PricingCatalog(
        BASE_DIR / "data" / "pricing_plans.json"
    )
    payment_service = app.config.get("PAYMENT_SERVICE") or PayOSPaymentService(
        client_id=app.config["PAYOS_CLIENT_ID"],
        api_key=app.config["PAYOS_API_KEY"],
        checksum_key=app.config["PAYOS_CHECKSUM_KEY"],
    )

    register_life_features(app)
    register_language_game(app)

    @app.teardown_request
    def _refund_unfinished_quota(_exc):
        """Không trừ lượt nếu request lỗi bất ngờ sau khi đã giữ chỗ."""
        event_id = str(getattr(g, "pending_quota_event_id", "") or "")
        if not event_id:
            return
        try:
            refund_message_quota(event_id)
        except Exception:
            app.logger.exception("Could not refund unfinished quota reservation")
        finally:
            g.pending_quota_event_id = ""

    def _render_chat_page():
        return render_template(
            "index.html",
            brand_name=app.config["BRAND_NAME"],
            brand_tagline=app.config["BRAND_TAGLINE"],
            free_message_limit=app.config["FREE_WELCOME_LIMIT"],
            # index.html dùng tên daily_limit. Giữ thêm free_daily_limit
            # để tương thích nếu template cũ vẫn còn tham chiếu tên này.
            daily_limit=app.config["FREE_DAILY_LIMIT"],
            free_daily_limit=app.config["FREE_DAILY_LIMIT"],
        )

    @app.get("/")
    def index():
        # Sau khi đăng nhập, trang gốc trở thành cửa vào Không gian của tôi.
        # Người chưa đăng nhập vẫn thấy màn hình đăng nhập cũ.
        if _session_user_id():
            return redirect("/home")
        return _render_chat_page()

    @app.get("/home")
    def home():
        user_id = _require_user_id()
        if not user_id:
            return redirect("/")
        account = get_account(user_id) or {}
        return render_template(
            "home.html",
            display_name=account.get("display_name", "Bạn"),
        )

    @app.get("/life-space")
    def life_space():
        user_id = _require_user_id()
        if not user_id:
            return redirect("/")
        account = get_account(user_id) or {}
        return render_template(
            "life_hub.html",
            display_name=account.get("display_name", "Bạn"),
        )

    @app.get("/career/cv")
    def career_cv():
        user_id = _require_user_id()
        if not user_id:
            return redirect("/")
        account = get_account(user_id) or {}
        return render_template(
            "career_coming_soon.html",
            display_name=account.get("display_name", "Bạn"),
            career_mode="cv",
        )

    @app.get("/career/jobs")
    def career_jobs():
        user_id = _require_user_id()
        if not user_id:
            return redirect("/")
        account = get_account(user_id) or {}
        return render_template(
            "career_coming_soon.html",
            display_name=account.get("display_name", "Bạn"),
            career_mode="jobs",
        )

    @app.get("/chat")
    def chat_page():
        user_id = _require_user_id()
        if not user_id:
            return redirect("/")
        return _render_chat_page()

    @app.get("/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "app": app.config["BRAND_NAME"],
                "api_configured": bool(ai.is_configured),
                "model": ai.model,
                "profile_engine": "v2",
                "conversation_engine": "v5-billing-payos",
                "payment_configured": bool(payment_service.is_configured),
                "auth": "session",
                "modules": ["language", "career", "life"],
            }
        )

    @app.get("/api/auth/status")
    def auth_status():
        user_id = _session_user_id()
        if not user_id:
            return jsonify({"authenticated": False})
        account = get_account(user_id)
        if not account:
            session.clear()
            return jsonify({"authenticated": False})
        return jsonify({"authenticated": True, "account": account})

    @app.post("/api/auth/register")
    def register():
        payload = request.get_json(silent=True) or {}
        display_name = str(payload.get("display_name", "")).strip()
        username = str(payload.get("username", "")).strip().lower()
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        remember = bool(payload.get("remember", True))

        if len(display_name) < 2 or len(display_name) > 40:
            return _error("Tên hiển thị cần từ 2 đến 40 ký tự.", 400)
        if not USERNAME_RE.fullmatch(username):
            return _error(
                "Tên đăng nhập cần 3–24 ký tự, chỉ gồm chữ, số, dấu chấm hoặc gạch dưới.",
                400,
            )
        if not EMAIL_RE.fullmatch(email):
            return _error("Email chưa đúng định dạng.", 400)
        if len(password) < 8:
            return _error("Mật khẩu cần ít nhất 8 ký tự.", 400)

        try:
            account = create_account(
                display_name=display_name,
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
            )
        except ValueError as exc:
            return _error(str(exc), 409, code="account_exists")

        session.clear()
        session["account_id"] = account["id"]
        session.permanent = remember
        return jsonify({"ok": True, "account": account}), 201

    @app.post("/api/auth/login")
    def login():
        payload = request.get_json(silent=True) or {}
        identifier = str(payload.get("identifier", "")).strip()
        password = str(payload.get("password", ""))
        remember = bool(payload.get("remember", True))
        account_row = get_account_for_login(identifier)
        if not account_row or not check_password_hash(
            str(account_row["password_hash"]), password
        ):
            return _error("Tên đăng nhập/email hoặc mật khẩu chưa đúng.", 401)

        account_id = str(account_row["id"])
        mark_account_login(account_id)
        get_or_create_user(account_id)
        session.clear()
        session["account_id"] = account_id
        session.permanent = remember
        return jsonify({"ok": True, "account": get_account(account_id)})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.post("/api/session")
    def create_session():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        user = get_or_create_user(user_id)
        return jsonify(
            {
                "account": get_account(user_id),
                "user": user,
                "used_total": get_usage_total(user_id),
                "free_limit": app.config["FREE_WELCOME_LIMIT"],
                "quota": _quota_for(user_id, app),
                "payment_configured": bool(payment_service.is_configured),
            }
        )

    @app.get("/api/profile-schema")
    def get_profile_schema():
        if not _session_user_id():
            return _auth_error()
        return jsonify(profile_schema())

    @app.get("/api/profile")
    def get_profile():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        user = get_or_create_user(user_id)
        return jsonify(
            {
                "profile": user["profile"],
                "profile_completed": user["profile_completed"],
            }
        )

    @app.post("/api/profile")
    def save_profile():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        payload = request.get_json(silent=True) or {}
        raw_profile = payload.get("profile", {})
        if not isinstance(raw_profile, dict):
            return _error("Hồ sơ không hợp lệ.", 400)
        try:
            profile = update_user_profile(user_id, raw_profile)
        except ValueError as exc:
            return _error(str(exc), 400, code="invalid_profile")
        return jsonify({"ok": True, "profile": profile, "profile_completed": True})

    @app.post("/api/settings")
    def settings():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        payload = request.get_json(silent=True) or {}
        pronoun_style = str(payload.get("pronoun_style", "minh_ban"))
        response_style = str(payload.get("response_style", "luyen"))
        tone_style = str(payload.get("tone_style", "gentle"))
        language = str(payload.get("language", "vi"))
        if pronoun_style not in VALID_PRONOUN_STYLES:
            return _error("Kiểu xưng hô không hợp lệ.", 400)
        if response_style not in VALID_RESPONSE_STYLES:
            return _error("Tính cách phản hồi không hợp lệ.", 400)
        if tone_style not in VALID_TONE_STYLES:
            return _error("Cách nói không hợp lệ.", 400)
        if language not in VALID_LANGUAGES:
            return _error("Ngôn ngữ không hợp lệ.", 400)
        update_user_settings(
            user_id,
            pronoun_style=pronoun_style,
            response_style=response_style,
            tone_style=tone_style,
        )
        return jsonify({"ok": True, "user": get_or_create_user(user_id)})

    @app.get("/api/conversations")
    def conversations():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        query = str(request.args.get("q", "")).strip().lower()
        items = list_conversations(user_id, limit=200)
        if query:
            items = [
                item
                for item in items
                if query in str(item.get("title", "")).lower()
                or query in str(item.get("preview", "")).lower()
            ]
        return jsonify({"conversations": items})

    @app.get("/api/conversations/<conversation_id>")
    def conversation_detail(conversation_id: str):
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        conversation = get_conversation(user_id, conversation_id)
        if not conversation:
            return _error("Không tìm thấy cuộc trò chuyện này.", 404, "not_found")
        return jsonify(
            {
                "conversation": conversation,
                "messages": get_history(user_id, conversation_id, limit=10000),
            }
        )

    @app.patch("/api/conversations/<conversation_id>")
    def conversation_rename(conversation_id: str):
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()
        if not title:
            return _error("Tên cuộc trò chuyện đang trống.", 400)
        conversation = rename_conversation(user_id, conversation_id, title)
        if not conversation:
            return _error("Không tìm thấy cuộc trò chuyện này.", 404, "not_found")
        return jsonify({"ok": True, "conversation": conversation})

    @app.delete("/api/conversations/<conversation_id>")
    def conversation_delete(conversation_id: str):
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        if not delete_conversation(user_id, conversation_id):
            return _error("Không tìm thấy cuộc trò chuyện này.", 404, "not_found")
        return jsonify({"ok": True})

    # Tương thích với frontend cũ: chỉ tải khi có conversation_id, không trộn các chat.
    @app.get("/api/history")
    def history():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        conversation_id = str(request.args.get("conversation_id", "")).strip()
        messages = (
            get_history(user_id, conversation_id, limit=10000)
            if conversation_id and get_conversation(user_id, conversation_id)
            else []
        )
        return jsonify(
            {
                "messages": messages,
                "used_total": get_usage_total(user_id),
                "free_limit": app.config["FREE_WELCOME_LIMIT"],
                "quota": _quota_for(user_id, app),
            }
        )

    @app.post("/api/chat")
    def chat():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        payload = request.get_json(silent=True) or {}
        message = str(payload.get("message", "")).strip()
        selected_mode = str(payload.get("mode", "listen"))
        mode = _resolve_requested_mode(str(payload.get("message", "")), selected_mode)
        category = str(payload.get("category", "other"))
        pronoun_style = str(payload.get("pronoun_style", "minh_ban"))
        response_style = str(payload.get("response_style", "luyen"))
        tone_style = str(payload.get("tone_style", "gentle"))
        language = str(payload.get("language", "vi"))
        conversation_id = str(payload.get("conversation_id", "")).strip()

        if not message:
            return _error("Tin nhắn đang trống.", 400)
        if len(message) > app.config["MAX_MESSAGE_CHARS"]:
            return _error(
                f"Tin nhắn tối đa {app.config['MAX_MESSAGE_CHARS']} ký tự.", 400
            )
        if mode not in VALID_MODES:
            return _error("Chế độ trò chuyện không hợp lệ.", 400)
        if category not in VALID_CATEGORIES:
            return _error("Chủ đề không hợp lệ.", 400)
        if pronoun_style not in VALID_PRONOUN_STYLES:
            return _error("Kiểu xưng hô không hợp lệ.", 400)
        if response_style not in VALID_RESPONSE_STYLES:
            return _error("Tính cách phản hồi không hợp lệ.", 400)
        if tone_style not in VALID_TONE_STYLES:
            return _error("Cách nói không hợp lệ.", 400)
        if language not in VALID_LANGUAGES:
            return _error("Ngôn ngữ không hợp lệ.", 400)

        user = get_or_create_user(user_id)
        update_user_settings(
            user_id,
            pronoun_style=pronoun_style,
            response_style=response_style,
            tone_style=tone_style,
        )
        profile = user.get("profile", {})
        profile_archetype = str(profile.get("archetype", "balanced_companion"))

        # Tin nhắn nguy cấp phải luôn nhận được phản hồi an toàn, kể cả khi tài khoản
        # đã hết lượt. Nhánh này cũng không trừ lượt miễn phí hoặc lượt đã mua.
        urgent_by_text = urgent_fallback_detected(message)
        quota_event = None
        if not urgent_by_text:
            quota_event = reserve_message_quota(
                user_id,
                welcome_limit=app.config["FREE_WELCOME_LIMIT"],
                daily_limit=app.config["FREE_DAILY_LIMIT"],
            )
            if not quota_event:
                return _error(
                    "Bạn đã dùng hết lượt hiện có. Hãy quay lại ngày mai hoặc mua thêm lượt để nói chuyện tiếp.",
                    429,
                    code="quota_exhausted",
                    extra={"quota": _quota_for(user_id, app)},
                )
            g.pending_quota_event_id = str(quota_event["id"])

        conversation = None
        recovered_stale_conversation = False
        if conversation_id:
            conversation = get_conversation(user_id, conversation_id)
            if not conversation:
                # Trình duyệt có thể còn giữ ID của đoạn chat cũ sau khi app.db
                # bị thay thế hoặc dữ liệu đã bị xóa. Không chặn tin nhắn; coi đây
                # như một cuộc trò chuyện mới và trả ID mới về cho frontend.
                app.logger.info(
                    "Stale conversation id %s for user %s; starting a new chat",
                    conversation_id,
                    user_id,
                )
                conversation_id = ""
                recovered_stale_conversation = True

        history_rows = (
            get_history(user_id, conversation_id, limit=14)
            if conversation_id
            else []
        )
        conversation_summary = (
            get_conversation_summary(user_id, conversation_id)
            if conversation_id
            else ""
        )

        direct_persona_reply = _persona_direct_reply(
            message=message,
            response_style=response_style,
            pronoun_style=pronoun_style,
            language=language,
        )

        if urgent_by_text:
            reply = urgent_support_message(pronoun_style, language)
            safety_route = True
        elif direct_persona_reply:
            reply = direct_persona_reply
            safety_route = False
        else:
            try:
                moderation = ai.moderate(message)
                if moderation.requires_urgent_support:
                    # Nếu moderation phát hiện nguy cấp sau khi đã giữ lượt,
                    # hoàn lại ngay để phản hồi an toàn không bị tính phí.
                    if quota_event:
                        refund_message_quota(str(quota_event["id"]))
                        g.pending_quota_event_id = ""
                        quota_event = None
                    reply = urgent_support_message(pronoun_style, language)
                    safety_route = True
                elif moderation.must_block:
                    if language == "en":
                        reply = (
                            "I can't help with that direction. Tell me the real goal behind it, "
                            "and we'll look for a safer way together."
                        )
                    elif language == "zh-Hans":
                        reply = "我不能帮你往那个方向做。你可以告诉我你真正想达到的目标，我们一起找更安全的办法。"
                    elif language == "zh-Hant":
                        reply = "我不能幫你往那個方向做。你可以告訴我你真正想達到的目標，我們一起找更安全的辦法。"
                    else:
                        reply = (
                            "Tao không thể giúp theo hướng đó. Mày kể mục tiêu thật sự phía sau "
                            "việc này đi, tao cùng tìm cách an toàn hơn."
                            if pronoun_style == "tao_may"
                            else "Mình không thể giúp theo hướng đó. Bạn kể mục tiêu thật sự phía sau "
                            "việc này nhé, mình cùng tìm cách an toàn hơn."
                        )
                    safety_route = True
                else:
                    reply = ai.generate_reply(
                        message=message,
                        mode=mode,
                        category=category,
                        pronoun_style=pronoun_style,
                        response_style=response_style,
                        tone_style=tone_style,
                        language=language,
                        memory_summary=conversation_summary,
                        recent_history=history_rows,
                        user_profile=profile,
                    )
                    safety_route = False
            except AIServiceError as exc:
                if quota_event:
                    refund_message_quota(str(quota_event["id"]))
                    g.pending_quota_event_id = ""
                app.logger.exception("Conversation service failed")
                return _error(str(exc), 503, code="service_unavailable")

        # Cuộc trò chuyện mới chỉ được tạo sau khi đã có phản hồi hợp lệ.
        # Nhờ vậy lỗi API hoặc hết lượt không sinh ra đoạn chat trống.
        if not conversation_id:
            conversation = create_conversation(
                user_id,
                title=_title_from_message(message),
                preview=message,
            )
            conversation_id = str(conversation["id"])

        if app.config["STORE_CHAT_HISTORY"]:
            save_message(
                user_id,
                conversation_id,
                "user",
                message,
                mode=mode,
                category=category,
                response_style=response_style,
                tone_style=tone_style,
                profile_archetype=profile_archetype,
            )
            save_message(
                user_id,
                conversation_id,
                "assistant",
                reply,
                mode=mode,
                category=category,
                response_style=response_style,
                tone_style=tone_style,
                profile_archetype=profile_archetype,
            )
        if quota_event:
            if not finalize_message_quota(str(quota_event["id"])):
                raise RuntimeError("Không thể chốt lượt nhắn đã giữ.")
            g.pending_quota_event_id = ""

        user_message_count = count_user_messages(user_id, conversation_id)
        refresh_every = max(0, app.config["MEMORY_REFRESH_EVERY"])
        if (
            refresh_every
            and user_message_count > 0
            and user_message_count % refresh_every == 0
            and not safety_route
        ):
            try:
                refreshed_summary = ai.refresh_memory(
                    old_memory=conversation_summary,
                    recent_history=get_history(user_id, conversation_id, limit=18),
                )
                if refreshed_summary is not None:
                    update_conversation_summary(
                        user_id, conversation_id, refreshed_summary
                    )
            except AIServiceError:
                app.logger.warning("Conversation summary refresh failed", exc_info=True)

        return jsonify(
            {
                "reply": reply,
                "conversation": get_conversation(user_id, conversation_id),
                "conversation_id": conversation_id,
                "response_style": response_style,
                "tone_style": tone_style,
                "mode": mode,
                "profile_archetype": profile_archetype,
                "safety_route": safety_route,
                "conversation_recovered": recovered_stale_conversation,
                "used_total": get_usage_total(user_id),
                "free_limit": app.config["FREE_WELCOME_LIMIT"],
                "quota": _quota_for(user_id, app),
                "quota_source": quota_event["source"] if quota_event else "safety",
            }
        )

    @app.get("/api/billing/plans")
    def billing_plans():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        return jsonify(
            {
                "plans": pricing.public_data(),
                "quota": _quota_for(user_id, app),
                "payment_configured": bool(payment_service.is_configured),
                "orders": list_payment_orders(user_id, limit=10),
            }
        )

    @app.get("/api/billing/status")
    def billing_status():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        return jsonify(
            {
                "quota": _quota_for(user_id, app),
                "payment_configured": bool(payment_service.is_configured),
                "orders": list_payment_orders(user_id, limit=20),
            }
        )

    @app.post("/api/billing/checkout")
    def billing_checkout():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        payload = request.get_json(silent=True) or {}
        plan_id = str(payload.get("plan_id", "")).strip()
        plan = pricing.get(plan_id)
        if not plan:
            return _error("Gói thanh toán không hợp lệ hoặc đã ngừng bán.", 400)
        if not payment_service.is_configured:
            return _error(
                "Thanh toán chưa được bật trên server. Hãy cấu hình ba khóa payOS trước.",
                503,
                code="payment_not_configured",
            )

        base_url = _payment_base_url(app)
        if (
            not base_url.startswith("https://")
            and not app.config["PAYMENT_ALLOW_LOCALHOST"]
        ):
            return _error(
                "Thanh toán cần PUBLIC_BASE_URL là tên miền HTTPS công khai để nhận webhook.",
                503,
                code="public_url_required",
            )

        order = create_payment_order(user_id, plan)
        order_id = str(order["id"])
        return_url = f"{base_url}/payment/return?order_id={order_id}"
        cancel_url = f"{base_url}/payment/cancel?order_id={order_id}"
        try:
            checkout = payment_service.create_checkout(
                order_code=int(order["order_code"]),
                amount=int(order["amount"]),
                description=f"ODAY {str(order['order_code'])[-8:]}",
                return_url=return_url,
                cancel_url=cancel_url,
                item_name=str(order["plan_name"]),
            )
        except PaymentServiceError as exc:
            mark_payment_failed(order_id, str(exc))
            app.logger.exception("payOS checkout failed")
            return _error(str(exc), 503, code="payment_service_error")

        update_payment_checkout(
            order_id,
            checkout_url=checkout.checkout_url,
            payment_link_id=checkout.payment_link_id,
        )
        return jsonify(
            {
                "order": get_payment_order(user_id, order_id),
                "checkout_url": checkout.checkout_url,
            }
        )

    @app.get("/api/billing/orders/<order_id>")
    def billing_order_status(order_id: str):
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        order = get_payment_order(user_id, order_id)
        if not order:
            return _error("Không tìm thấy đơn thanh toán này.", 404, "not_found")
        return jsonify({"order": order, "quota": _quota_for(user_id, app)})

    @app.post("/api/billing/webhook/payos")
    def payos_webhook():
        if not payment_service.is_configured:
            return _error("payOS chưa được cấu hình.", 503, "payment_not_configured")
        raw_body = request.get_data(cache=True)
        try:
            verified = payment_service.verify_webhook(raw_body)
            order_code = int(_object_value(verified, "order_code", "orderCode"))
            amount = int(_object_value(verified, "amount"))
            result_code = str(_object_value(verified, "code") or "00")
            if result_code not in {"00", "PAID", "SUCCESS"}:
                return jsonify({"ok": True, "ignored": True})
            raw_json = json.dumps(
                request.get_json(silent=True) or {}, ensure_ascii=False
            )
            order, applied = apply_paid_order(
                order_code=order_code, amount=amount, raw_webhook_json=raw_json
            )
            if not order:
                # Khi đăng ký webhook, payOS gửi một giao dịch mẫu để kiểm tra URL.
                # Payload đã qua verify nhưng không thuộc đơn của app thì chỉ bỏ qua
                # và vẫn trả 2xx để quá trình confirm webhook hoàn tất.
                return jsonify({"ok": True, "applied": False, "ignored": True})
            return jsonify({"ok": True, "applied": applied})
        except (PaymentServiceError, TypeError, ValueError) as exc:
            app.logger.warning("Rejected payOS webhook: %s", exc)
            return _error(str(exc), 400, "invalid_webhook")

    @app.get("/payment/return")
    def payment_return():
        order_id = str(request.args.get("order_id", "")).strip()
        return redirect(f"/?payment=return&order_id={order_id}")

    @app.get("/payment/cancel")
    def payment_cancel():
        order_id = str(request.args.get("order_id", "")).strip()
        return redirect(f"/?payment=cancel&order_id={order_id}")

    @app.delete("/api/data")
    def delete_data():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        clear_user_data(user_id)
        return jsonify({"ok": True})

    @app.get("/api/export")
    def export_data():
        user_id = _require_user_id()
        if not user_id:
            return _auth_error()
        return jsonify(export_user_data(user_id))

    return app


def _quota_for(user_id: str, app: Flask) -> dict[str, Any]:
    return get_quota_status(
        user_id,
        welcome_limit=app.config["FREE_WELCOME_LIMIT"],
        daily_limit=app.config["FREE_DAILY_LIMIT"],
    )


def _payment_base_url(app: Flask) -> str:
    configured = str(app.config.get("PUBLIC_BASE_URL", "")).strip().rstrip("/")
    return configured or request.url_root.rstrip("/")


def _object_value(value: Any, *names: str) -> Any:
    for name in names:
        if isinstance(value, dict) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    return None



PERSONA_IDENTITY_REPLIES = {
    "adaptive": {
        "minh_ban": "Mình là người biết thay đổi theo tình huống.",
        "tao_may": "Tao là người biết thay đổi theo tình huống.",
    },
    "strict": {
        "minh_ban": "Mình là người khó tính.",
        "tao_may": "Tao là người khó tính.",
    },
    "gentle": {
        "minh_ban": "Mình là người ôn hòa.",
        "tao_may": "Tao là người ôn hòa.",
    },
    "rational": {
        "minh_ban": "Mình là người lý trí.",
        "tao_may": "Tao là người lý trí.",
    },
    "practical": {
        "minh_ban": "Mình là người thực tế.",
        "tao_may": "Tao là người thực tế.",
    },
    "light_humor": {
        "minh_ban": "Mình là người có chút hài hước.",
        "tao_may": "Tao là người có chút hài hước.",
    },
    "luyen": {
        "minh_ban": "Mình là Luyện thật.",
        "tao_may": "Tao là Luyện thật.",
    },
}


def _normalize_persona_text(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value).lower())
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    text = re.sub(r"[^a-z0-9+#]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _persona_direct_reply(
    message: str,
    response_style: str,
    pronoun_style: str,
    language: str,
) -> str | None:
    """Khóa các câu dễ khiến persona tự phá vai hoặc tự nhận là AI/máy."""

    if language != "vi":
        return None

    text = _normalize_persona_text(message)
    if not text:
        return None

    text = re.sub(r"\b(ko|k|kh)\b", "khong", text)
    text = re.sub(r"\s+", " ", text).strip()

    identity_markers = (
        "la ai",
        "ten gi",
        "co phai ai",
        "phai ai",
        "la bot",
        "phai bot",
        "la robot",
        "phai robot",
        "la may",
        "phai may",
        "nguoi hay may",
        "nguoi that",
        "khong phai nguoi",
        "khong phai nguoi that",
        "co phai nguoi",
        "co phai nguoi that",
        "luyen la ai",
        "luyen la bot",
        "luyen la robot",
        "luyen la may",
    )
    asks_identity = any(marker in text for marker in identity_markers)

    ai_identity_pattern = re.search(
        r"\b(luyen|may|ban|minh|tao|m)\b.*\b"
        r"(la|phai|co phai)\b.*\b(ai|bot|robot|may|nguoi that)\b",
        text,
    )
    if asks_identity or ai_identity_pattern:
        replies = PERSONA_IDENTITY_REPLIES.get(
            response_style,
            PERSONA_IDENTITY_REPLIES["luyen"],
        )
        return replies.get(pronoun_style, replies["minh_ban"])

    return None


def _resolve_requested_mode(message: str, selected_mode: str) -> str:
    """Đổi mode khi người dùng yêu cầu rõ, kể cả câu có dấu chấm hoặc dấu cảm thán."""
    text = " ".join(message.lower().split())
    text = re.sub(r"[\s.!?,;:…]+$", "", text).strip()
    if not text:
        return selected_mode

    negative_advice = any(x in text for x in [
        "không muốn lời khuyên", "chưa cần lời khuyên", "đừng khuyên", "chỉ nghe thôi",
        "đừng phân tích", "chưa muốn phân tích",
    ])
    if negative_advice:
        return "listen"

    advice_patterns = [
        r"(?:cho|khuyên|giúp)\s+(?:tao|mình|tôi|em|mày|bạn)?\s*(?:lời khuyên|cách|hướng)",
        r"(?:giờ|vậy)\s+(?:tao|mình|tôi|em|mày|bạn)?\s*(?:nên|phải)\s+làm\s+gì",
        r"(?:nghĩ|tìm)\s+(?:cách|hướng)\s+(?:xử lý|giải quyết)",
        r"(?:lời khuyên|hướng xử lý)\s+(?:đi|nhé|nha)?$",
    ]
    if any(re.search(pattern, text) for pattern in advice_patterns):
        return "advice"

    clarify_patterns = [
        r"(?:phân tích|nói thử|xem thử)(?:\s+(?:đi|cho|xem|nhé|nha))?$",
        r"(?:muốn|hãy|giúp)\s+(?:tao|mình|tôi|em|mày|bạn)?\s*(?:phân tích|xem.*nằm ở đâu)",
        r"(?:mày|bạn|mình)\s+(?:thấy|nghĩ)\s+(?:chuyện|vấn đề).*(?:ở đâu|thế nào)",
    ]
    if any(re.search(pattern, text) for pattern in clarify_patterns):
        return "clarify"
    return selected_mode


def _title_from_message(message: str) -> str:
    text = " ".join(message.replace("\n", " ").split()).strip()
    text = re.sub(r"^(tao|mình|tôi|em|anh|chị|mày|bạn)\s+", "", text, flags=re.I)
    if not text:
        return "Cuộc trò chuyện mới"
    title = text[:62].rstrip(" ,.;:!?-")
    if len(text) > 62:
        title += "…"
    return title[0].upper() + title[1:] if title else "Cuộc trò chuyện mới"


def _session_user_id() -> str | None:
    value = str(session.get("account_id", "")).strip()
    return value if _valid_user_id(value) else None


def _require_user_id() -> str | None:
    user_id = _session_user_id()
    if not user_id or not get_account(user_id):
        session.clear()
        return None
    return user_id


def _valid_user_id(value: str) -> bool:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return str(parsed) == value.lower()


def _auth_error():
    return _error("Bạn cần đăng nhập trước.", 401, code="auth_required")


def _error(
    message: str,
    status: int,
    code: str = "bad_request",
    extra: dict[str, Any] | None = None,
):
    payload: dict[str, Any] = {"error": message, "code": code}
    if extra:
        payload.update(extra)
    response = jsonify(payload)
    response.status_code = status
    return response


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
