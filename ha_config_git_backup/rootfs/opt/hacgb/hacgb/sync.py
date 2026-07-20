"""把 HA 配置目录同步到 git 工作副本。

用 rsync 而非 shutil：需要 --delete 语义（源端删除传播到目标端）和
一套成熟的 exclude 匹配规则，自行实现容易出微妙的差错。
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .errors import SyncError

_LOGGER = logging.getLogger(__name__)


def sync_config(source: Path, dest: Path, exclude_file: Path) -> None:
    """把 source 同步到 dest，失败时抛 SyncError。

    source 通常是 /homeassistant（注意不是 /config——在当前 Supervisor 中
    /config 指的是 add-on 自己的配置目录）。
    """
    if not source.is_dir():
        raise SyncError(f"Configuration directory does not exist: {source}")
    if not exclude_file.is_file():
        raise SyncError(f"Exclude list does not exist: {exclude_file}")

    dest.mkdir(parents=True, exist_ok=True)

    # 结尾的斜杠有意义：源端加斜杠表示"同步目录内容"而非"同步目录本身"。
    result = subprocess.run(
        [
            "rsync",
            "-a",
            "--delete",
            f"--exclude-from={exclude_file}",
            f"{source}/",
            f"{dest}/",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise SyncError(
            f"rsync failed (exit code {result.returncode}): {result.stderr.strip()}"
        )

    _LOGGER.debug("Synced %s -> %s", source, dest)
