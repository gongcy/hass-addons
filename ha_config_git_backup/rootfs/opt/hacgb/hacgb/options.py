"""读取 Supervisor 写入的 add-on 选项。

刻意不用 bashio 之类的 HA 专有工具：那样这个模块就无法脱离 HA 环境测试。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    """一次运行的全部配置。不可变，避免被中途改写。

    repo_url 默认为空是有意的：面向公开发布，不能内置任何默认仓库地址，
    否则用户未配置即启动会把自己的配置推向一个陌生地址。
    """

    repo_url: str = ""
    branch: str = "main"
    interval: int = 86400
    username: str = "oauth2"
    token: str = ""
    host_key: str = ""
    exclude: tuple[str, ...] = ()
    commit_author_name: str = "HA Config Backup"
    commit_author_email: str = "ha-config-backup@local"
    dry_run: bool = False
    notify_on_failure: bool = True

    @classmethod
    def load(cls, path: Path) -> "Config":
        raw = cls._read(path)
        return cls(
            repo_url=str(cls._pick(raw, "repo_url", "")),
            branch=str(cls._pick(raw, "branch", "main")),
            interval=int(cls._pick(raw, "interval", 86400)),
            username=str(cls._pick(raw, "username", "oauth2")),
            token=str(cls._pick(raw, "token", "")),
            host_key=str(cls._pick(raw, "host_key", "")),
            exclude=cls._pick_list(raw, "exclude"),
            commit_author_name=str(
                cls._pick(raw, "commit_author_name", "HA Config Backup")
            ),
            commit_author_email=str(
                cls._pick(raw, "commit_author_email", "ha-config-backup@local")
            ),
            dry_run=bool(cls._pick(raw, "dry_run", False)),
            notify_on_failure=bool(cls._pick(raw, "notify_on_failure", True)),
        )

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _LOGGER.warning("Options file not found, using defaults: %s", path)
            return {}
        except (json.JSONDecodeError, OSError) as err:
            _LOGGER.warning("Options file unreadable, using defaults: %s", err)
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _pick(raw: dict[str, Any], key: str, default: Any) -> Any:
        """取值。只有键缺失或值为 null 时才回退默认值。

        注意判断的是 `is None` 而不是真假：dry_run=False 和 interval=0
        都是合法配置，不能被当作"未设置"。
        """
        value = raw.get(key)
        return default if value is None else value

    @staticmethod
    def _pick_list(raw: dict[str, Any], key: str) -> tuple[str, ...]:
        """取列表型选项。非列表值一律当空处理，不让它炸掉启动。"""
        value = raw.get(key)
        if not isinstance(value, list):
            return ()
        return tuple(str(item) for item in value)
