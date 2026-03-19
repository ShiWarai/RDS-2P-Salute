"""Утилиты для URL Redis (без утечки секретов в логи)."""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def redact_redis_url(url: str) -> str:
    """Возвращает URL с заменой пароля на `***` для безопасного логирования."""
    p = urlparse(url)
    if not p.password:
        return url
    host = p.hostname or ""
    port = f":{p.port}" if p.port else ""
    if p.username:
        netloc = f"{p.username}:***@{host}{port}"
    else:
        netloc = f"***@{host}{port}"
    return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))
