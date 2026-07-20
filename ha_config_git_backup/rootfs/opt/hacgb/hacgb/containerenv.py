"""读取 Supervisor 注入的容器环境变量。

s6-overlay 把容器环境变量存进 /run/s6/container_environment/（一个变量一个
文件），只有走 `with-contenv` 的服务才拿得到；Dockerfile 的 CMD 作为 legacy
service 拉起，进程环境里一个都没有。

实测后果：SUPERVISOR_TOKEN 读不到 → 失败通知永远发不出去 → 备份挂掉也没人
知道。所以这里必须回退到 s6 的目录去读。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Mapping

_LOGGER = logging.getLogger(__name__)

S6_CONTAINER_ENVIRONMENT = Path("/run/s6/container_environment")


def read_container_env(
    name: str,
    environ: Mapping[str, str] | None = None,
    s6_dir: Path = S6_CONTAINER_ENVIRONMENT,
) -> str | None:
    """取容器环境变量，先看进程环境，再回退 s6 目录。

    取不到返回 None。s6 写的文件末尾带换行，必须剥掉——否则
    `Bearer <token>\\n` 会把 HTTP 头写坏。
    """
    if environ is None:
        environ = os.environ

    value = environ.get(name)
    if value:
        return value

    try:
        value = (s6_dir / name).read_text(encoding="utf-8").strip()
    except (FileNotFoundError, NotADirectoryError, OSError) as err:
        _LOGGER.debug("Could not read %s from the s6 environment directory: %s", name, err)
        return None

    return value or None
