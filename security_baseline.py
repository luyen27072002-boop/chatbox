from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from flask import Flask, current_app, jsonify, request, session
from werkzeug.middleware.proxy_fix import ProxyFix


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
EXEMPT_ORIGIN_PATHS = {"/api/billing/webhook/payos"}


@dataclass(frozen=True)
class RateRule:
    path: str
    methods: frozenset[str]
    limit: int
    window_seconds: int
    actor: str = "auto"  # auto | ip | user
    prefix: bool = False

    def matches(self, path: str, method: str) -> bool:
        if method not in self.methods:
            return False
        return path.startswith(self.path) if self.prefix else path == self.path


RATE_RULES = (
    RateRule("/api/auth/login", frozenset({"POST"}), 10, 10 * 60, "ip"),
    RateRule("/api/auth/register", frozenset({"POST"}), 5, 60 * 60, "ip"),
    RateRule("/api/chat", frozenset({"POST"}), 30, 60, "user"),
    RateRule("/api/language/respond", frozenset({"POST"}), 40, 60, "user"),
    RateRule("/api/astrology/chart", frozenset({"POST"}), 10, 60 * 60, "user"),
    RateRule("/api/astrology/ask", frozenset({"POST"}), 30, 60, "user"),
    RateRule("/api/career/cv/improve", frozenset({"POST"}), 12, 60 * 60, "user"),
    RateRule("/api/career/interview/answer", frozenset({"POST"}), 30, 60, "user"),
    RateRule("/api/career/jobs/search", frozenset({"GET"}), 30, 10 * 60, "user"),
    RateRule("/api/career/jobs/analyze", frozenset({"POST"}), 40, 60, "user"),
    RateRule("/api/billing/checkout", frozenset({"POST"}), 10, 10 * 60, "user"),
    RateRule("/api/account", frozenset({"DELETE"}), 5, 60 * 60, "user"),
    RateRule("/api/", frozenset({"POST", "PUT", "PATCH", "DELETE"}), 180, 60, "auto", prefix=True),
)


class InMemoryRateLimiter:
    """Small beta-grade limiter.

    This is deliberately dependency-free so it can be added without touching the
    deployment stack. It is sufficient for one small Render instance. When the app
    scales to multiple instances, replace this with a shared Redis-backed limiter.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._ops = 0

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry = max(1, int(window_seconds - (now - bucket[0]))) if bucket else window_seconds
                return False, retry
            bucket.append(now)
            self._ops += 1
            if self._ops % 1000 == 0:
                self._cleanup(now)
            return True, 0

    def _cleanup(self, now: float) -> None:
        stale = []
        for key, bucket in self._events.items():
            if not bucket or now - bucket[-1] > 7200:
                stale.append(key)
        for key in stale:
            self._events.pop(key, None)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_production(app: Flask) -> bool:
    if app.config.get("TESTING"):
        return False
    if app.config.get("SECURITY_FORCE_PRODUCTION") is True:
        return True
    if app.config.get("SECURITY_FORCE_PRODUCTION") is False:
        return False
    name = str(os.getenv("APP_ENV", os.getenv("FLASK_ENV", ""))).strip().lower()
    return name in {"prod", "production"} or _bool_env("RENDER", False)


def _actor_hash(raw: str) -> str:
    secret = str(current_app.config.get("SECRET_KEY", ""))
    digest = hashlib.sha256(f"{secret}|{raw}".encode("utf-8", "ignore")).hexdigest()
    return digest[:16]


def _client_ip() -> str:
    return str(request.remote_addr or "unknown")


def _rule_actor(rule: RateRule) -> str:
    user_id = str(session.get("account_id", "") or "").strip()
    if rule.actor == "user" and user_id:
        return f"u:{_actor_hash(user_id)}"
    if rule.actor == "auto" and user_id:
        return f"u:{_actor_hash(user_id)}"
    return f"ip:{_actor_hash(_client_ip())}"


def _origin_tuple(value: str) -> tuple[str, str, int | None] | None:
    try:
        parsed = urlsplit(value)
    except Exception:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return parsed.scheme, parsed.hostname.lower(), parsed.port


def _allowed_origins(app: Flask) -> set[tuple[str, str, int | None]]:
    allowed: set[tuple[str, str, int | None]] = set()
    base = str(app.config.get("PUBLIC_BASE_URL", "") or "").strip()
    if base:
        item = _origin_tuple(base)
        if item:
            allowed.add(item)
    try:
        item = _origin_tuple(request.host_url)
        if item:
            allowed.add(item)
    except RuntimeError:
        pass
    return allowed


def _same_origin_ok(app: Flask) -> bool:
    if request.method in SAFE_METHODS or request.path in EXEMPT_ORIGIN_PATHS:
        return True
    if not request.path.startswith("/api/"):
        return True

    origin = str(request.headers.get("Origin", "") or "").strip()
    referer = str(request.headers.get("Referer", "") or "").strip()
    supplied = origin or referer
    if not supplied:
        # JSON APIs are not form-postable cross-origin without a CORS preflight.
        # SameSite=Lax remains the primary browser CSRF baseline for requests that
        # omit both Origin and Referer.
        return True
    candidate = _origin_tuple(supplied)
    return bool(candidate and candidate in _allowed_origins(app))


def log_security_event(event: str, *, level: int = logging.WARNING, **fields: Any) -> None:
    safe: dict[str, Any] = {"event": str(event)[:80]}
    for key, value in fields.items():
        if key.lower() in {"password", "secret", "token", "content", "message", "body"}:
            continue
        safe[str(key)[:40]] = str(value)[:200]
    current_app.logger.log(level, "SECURITY %s", safe)


def _security_headers(response, *, production: bool):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), usb=()")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")

    csp = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "form-action 'self'"
    )
    if production:
        csp += "; upgrade-insecure-requests"
    response.headers.setdefault("Content-Security-Policy", csp)

    if request.path.startswith("/api/") or request.path.startswith("/account/"):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")

    if production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


def register_security_baseline(app: Flask) -> None:
    production = _is_production(app)
    app.config["IS_PRODUCTION"] = production
    app.config.setdefault("MAX_CONTENT_LENGTH", int(os.getenv("MAX_REQUEST_BYTES", "1048576")))
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_PATH"] = "/"
    if production:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["PREFERRED_URL_SCHEME"] = "https"

    trusted_hosts = [x.strip() for x in os.getenv("TRUSTED_HOSTS", "").split(",") if x.strip()]
    if trusted_hosts:
        app.config["TRUSTED_HOSTS"] = trusted_hosts

    trust_proxy = _bool_env("TRUST_PROXY_HEADERS", production)
    if trust_proxy:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    secret = str(app.config.get("SECRET_KEY", ""))
    if production and (not secret or secret == "dev-change-me"):
        app.logger.critical(
            "SECURITY SECRET_KEY is still the development default. Set a long random SECRET_KEY before public launch."
        )

    limiter = InMemoryRateLimiter()
    app.extensions["security_rate_limiter"] = limiter

    @app.before_request
    def _security_before_request():
        if not _same_origin_ok(app):
            log_security_event("cross_origin_mutation_blocked", path=request.path)
            return jsonify({"error": "Yêu cầu không cùng nguồn bị từ chối.", "code": "origin_rejected"}), 403

        path = request.path
        method = request.method.upper()
        for rule in RATE_RULES:
            if not rule.matches(path, method):
                continue
            actor = _rule_actor(rule)
            key = f"{method}:{rule.path}:{actor}:{rule.limit}:{rule.window_seconds}"
            allowed, retry_after = limiter.allow(key, rule.limit, rule.window_seconds)
            if not allowed:
                log_security_event("rate_limit", path=path, actor=actor)
                response = jsonify({
                    "error": "Bạn thao tác quá nhanh. Hãy thử lại sau một lúc.",
                    "code": "rate_limited",
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

    @app.after_request
    def _security_after_request(response):
        response = _security_headers(response, production=production)
        if response.status_code in {401, 403, 429} or response.status_code >= 500:
            level = logging.ERROR if response.status_code >= 500 else logging.WARNING
            log_security_event(
                "http_security_status",
                level=level,
                status=response.status_code,
                path=request.path,
                method=request.method,
            )
        return response
