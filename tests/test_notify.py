import json
from urllib.error import URLError

import pytest

from hacgb.notify import NOTIFICATION_ID, Notifier


@pytest.fixture
def captured(monkeypatch):
    """拦截 urlopen，记录请求而不真的发出去。"""
    calls: list[dict] = []

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _fake_urlopen(request, timeout=None):
        calls.append(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": json.loads(request.data.decode("utf-8")),
            }
        )
        return _FakeResponse()

    monkeypatch.setattr("hacgb.notify.urllib.request.urlopen", _fake_urlopen)
    return calls


def test_posts_to_persistent_notification_endpoint(captured):
    Notifier("http://supervisor", "tok", enabled=True).failure("推送失败")
    assert captured[0]["url"] == (
        "http://supervisor/core/api/services/persistent_notification/create"
    )


def test_sends_bearer_token(captured):
    Notifier("http://supervisor", "tok-123", enabled=True).failure("推送失败")
    headers = {k.lower(): v for k, v in captured[0]["headers"].items()}
    assert headers["authorization"] == "Bearer tok-123"


def test_uses_stable_notification_id(captured):
    """固定 id：反复失败时覆盖同一条，而不是堆积几十条。"""
    Notifier("http://supervisor", "tok", enabled=True).failure("推送失败")
    assert captured[0]["body"]["notification_id"] == NOTIFICATION_ID


def test_message_is_in_body(captured):
    Notifier("http://supervisor", "tok", enabled=True).failure("远端仓库不可达")
    assert captured[0]["body"]["message"] == "远端仓库不可达"


def test_disabled_notifier_sends_nothing(captured):
    Notifier("http://supervisor", "tok", enabled=False).failure("推送失败")
    assert captured == []


def test_missing_token_sends_nothing(captured):
    Notifier("http://supervisor", None, enabled=True).failure("推送失败")
    assert captured == []


def test_network_failure_is_swallowed(monkeypatch):
    """通知失败绝不能中断备份主流程。"""

    def _boom(request, timeout=None):
        raise URLError("network down")

    monkeypatch.setattr("hacgb.notify.urllib.request.urlopen", _boom)
    Notifier("http://supervisor", "tok", enabled=True).failure("推送失败")
    # 没有异常逃出来即为通过。
