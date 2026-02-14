"""
Интеграционные тесты для POST /v1/webhook.
"""
import pytest

pytestmark = pytest.mark.integration


def _chatapp_payload(utterance: str, user_id: str = "test-user-1", new_session: bool = False):
    """Формирует payload в формате ChatApp (MESSAGE_TO_SKILL)."""
    return {
        "messageName": "MESSAGE_TO_SKILL",
        "uuid": {"sub": user_id},
        "payload": {
            "message": {
                "original_text": utterance,
                "normalized_text": utterance,
                "human_normalized_text": utterance,
            },
            "new_session": new_session,
            "intent": "",
        },
    }


def _legacy_payload(utterance: str, user_id: str = "test-user-1", new_session: bool = False):
    """Формирует payload в формате legacy SmartApp API."""
    return {
        "session": {"new": new_session},
        "request": {"original_utterance": utterance, "command": utterance},
        "version": "1.0",
        "uuid": {"sub": user_id},
    }


def test_webhook_bind_robot_returns_instruction(app_client):
    """«привяжи робота 0» — ответ с инструкцией ввести код (мок робота «подключён»)."""
    payload = _chatapp_payload("привяжи робота 0")
    resp = app_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "messageName" in data
    text = data.get("payload", {}).get("items", [{}])[0].get("bubble", {}).get("text", "")
    if not text:
        text = data.get("payload", {}).get("pronounceText", "")
    assert "код" in text.lower() or "привяз" in text.lower()


def test_webhook_help_returns_menu(app_client):
    """«помощь» — меню помощи."""
    payload = _chatapp_payload("помощь")
    resp = app_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    text = data.get("payload", {}).get("items", [{}])[0].get("bubble", {}).get("text", "")
    if not text:
        text = data.get("payload", {}).get("pronounceText", "")
    assert "служебн" in text.lower() or "раздел" in text.lower()


def test_webhook_command_without_binding(app_client):
    """«лапу» без привязки — «привяжите робота»."""
    payload = _chatapp_payload("лапу")
    resp = app_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    text = data.get("payload", {}).get("items", [{}])[0].get("bubble", {}).get("text", "")
    if not text:
        text = data.get("payload", {}).get("pronounceText", "")
    assert "привяж" in text.lower() or "робот" in text.lower()


def test_webhook_command_with_binding(app_client):
    """«лапу» с привязкой — ответ «Робот поднимает лапу», команда give_paw в моке."""
    payload_bind = _chatapp_payload("привяжи робота 0", user_id="user-bound")
    app_client.post("/v1/webhook", json=payload_bind)

    payload_code = _chatapp_payload("1234", user_id="user-bound")
    payload_code["payload"]["message"] = {
        "original_text": "1234",
        "normalized_text": "1234",
        "human_normalized_text": "1234",
    }
    app_client.post("/v1/webhook", json=payload_code)

    payload_cmd = _chatapp_payload("лапу", user_id="user-bound")
    resp = app_client.post("/v1/webhook", json=payload_cmd)
    assert resp.status_code == 200
    data = resp.json()
    text = data.get("payload", {}).get("items", [{}])[0].get("bubble", {}).get("text", "")
    if not text:
        text = data.get("payload", {}).get("pronounceText", "")
    assert "лапу" in text.lower() or "🐾" in text


def test_webhook_legacy_help(app_client):
    """Legacy payload «помощь» — меню помощи."""
    payload = _legacy_payload("помощь")
    resp = app_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    text = data.get("response", {}).get("text", "")
    assert "служебн" in text.lower() or "раздел" in text.lower()


def test_webhook_invalid_json(app_client):
    """Невалидный JSON — 400."""
    resp = app_client.post(
        "/v1/webhook",
        data="not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
