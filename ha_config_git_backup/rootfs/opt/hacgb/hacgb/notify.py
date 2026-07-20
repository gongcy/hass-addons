"""经 Supervisor 代理向 HA Core 推送持久化通知。

需要 config.yaml 中 homeassistant_api: true。
用标准库 urllib 而非 requests，避免为一次 POST 引入运行时依赖。
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

_LOGGER = logging.getLogger(__name__)

NOTIFICATION_ID = "ha_config_git_backup_failure"
_TIMEOUT_SECONDS = 15


class Notifier:
    """把失败暴露到 HA 界面上。"""

    def __init__(self, base_url: str, token: str | None, enabled: bool) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._enabled = enabled

    def failure(self, message: str) -> None:
        """发送失败通知。

        本方法永不抛异常：通知本身失败不该中断备份主流程。
        """
        if not self._enabled:
            return
        if not self._token:
            _LOGGER.warning("No SUPERVISOR_TOKEN, skipping persistent notification")
            return

        payload = json.dumps(
            {
                "title": "HA config backup failed",
                "message": message,
                # 固定 id 让反复失败覆盖同一条通知，而不是堆满通知栏。
                "notification_id": NOTIFICATION_ID,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self._base_url}/core/api/services/persistent_notification/create",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS):
                pass
        except (urllib.error.URLError, OSError) as err:
            _LOGGER.warning("Failed to send persistent notification: %s", err)
