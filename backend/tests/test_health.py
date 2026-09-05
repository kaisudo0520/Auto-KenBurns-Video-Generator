"""
/health 端點測試

一鍵啟動器（scripts/start.ps1）會分別「直連後端」與「經前端 proxy」讀取 /health，
比對 instance_id 以確認前端 proxy 指向的是同一個後端程序。
"""

import re

from fastapi.testclient import TestClient

from backend.main import app


def test_health_returns_status_and_service():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "Auto-KenBurns Video Generator"


def test_health_returns_process_identity():
    """instance_id 為本程序啟動時產生的 32 位 hex，pid 為正整數"""
    client = TestClient(app)
    body = client.get("/health").json()
    assert re.fullmatch(r"[0-9a-f]{32}", body["instance_id"])
    assert isinstance(body["pid"], int) and body["pid"] > 0


def test_health_instance_id_is_stable_within_process():
    """同一個程序內多次呼叫必須回傳同一個 instance_id，否則啟動器的比對會誤判"""
    client = TestClient(app)
    first = client.get("/health").json()["instance_id"]
    second = client.get("/health").json()["instance_id"]
    assert first == second


def test_resolve_instance_id_prefers_env(monkeypatch):
    """啟動器以 KENBURNS_INSTANCE_ID 注入，讓 uvicorn --workers N 的所有 worker 共用同一個識別"""
    from backend.main import resolve_instance_id

    monkeypatch.setenv("KENBURNS_INSTANCE_ID", "a" * 32)
    assert resolve_instance_id() == "a" * 32


def test_resolve_instance_id_generates_hex_without_env(monkeypatch):
    from backend.main import resolve_instance_id

    monkeypatch.delenv("KENBURNS_INSTANCE_ID", raising=False)
    generated = resolve_instance_id()
    assert re.fullmatch(r"[0-9a-f]{32}", generated)
    assert generated != resolve_instance_id()  # 未注入時每次呼叫各自產生


def test_resolve_instance_id_ignores_blank_env(monkeypatch):
    from backend.main import resolve_instance_id

    monkeypatch.setenv("KENBURNS_INSTANCE_ID", "   ")
    assert re.fullmatch(r"[0-9a-f]{32}", resolve_instance_id())
