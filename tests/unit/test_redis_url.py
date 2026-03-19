from app.utils.redis_url import redact_redis_url


def test_redact_redis_url_no_password():
    assert redact_redis_url("redis://localhost:6379/0") == "redis://localhost:6379/0"


def test_redact_redis_url_password_only():
    assert (
        redact_redis_url("redis://:secret@redis:6379/0")
        == "redis://***@redis:6379/0"
    )


def test_redact_redis_url_user_and_password():
    assert (
        redact_redis_url("redis://user:secret@host:6379/0")
        == "redis://user:***@host:6379/0"
    )
