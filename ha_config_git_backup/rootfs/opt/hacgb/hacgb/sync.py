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
    # --delete-excluded：之前已入库、后来才被排除的文件也要从工作副本删掉，
    # 否则它们会以旧内容永久留在仓库里（排除规则只能让它们"冻结"）。
    # 它会让排除规则不再保护接收端，所以 .git 必须另用 P（protect）规则保住，
    # 且要排在排除表前面——rsync 按顺序取第一条匹配的规则。
    result = subprocess.run(
        [
            "rsync",
            "-a",
            "--delete",
            "--delete-excluded",
            "--filter=P /.git/",
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
