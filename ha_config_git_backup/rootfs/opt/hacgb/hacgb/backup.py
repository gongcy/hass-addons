"""一轮备份的编排。

成功路径有三种结果，用枚举表达；失败一律抛 BackupError 子类。
这样调用方不必去查"返回码 2 是什么意思"。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .options import Config
from .repo import Repo
from .sync import sync_config

_LOGGER = logging.getLogger(__name__)


class Outcome(Enum):
    """一轮备份的成功结果。失败走异常，不在此列。"""

    PUSHED = "pushed"
    NO_CHANGES = "no_changes"
    DRY_RUN = "dry_run"


@dataclass
class BackupJob:
    config: Config
    source_dir: Path
    repo: Repo
    exclude_file: Path

    def run_once(self) -> Outcome:
        """执行一轮备份。失败时抛 BackupError 的子类。"""
        sync_config(self.source_dir, self.repo.path, self.exclude_file)

        if not self.repo.has_changes():
            _LOGGER.info("No changes, skipping this run")
            return Outcome.NO_CHANGES

        if self.config.dry_run:
            _LOGGER.info(
                "dry_run is on; the following changes will not be committed:\n%s",
                self.repo.show_changes(),
            )
            return Outcome.DRY_RUN

        self.repo.commit(
            self.config.commit_author_name, self.config.commit_author_email
        )
        self.repo.push(self.config.branch)
        _LOGGER.info("Backup pushed to %s", self.config.branch)
        return Outcome.PUSHED
