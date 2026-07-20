"""git 工作副本的初始化、提交与推送。

工作副本常驻 /data/repo（跨 HAOS 升级保留），因此每轮只需处理增量，
不必重新 clone。
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from .errors import CommitError, PushError, RemoteUnavailableError

_LOGGER = logging.getLogger(__name__)

DEFAULT_RETRY_DELAYS: tuple[float, ...] = (10, 30)


class Repo:
    """/data/repo 下的 git 工作副本。"""

    def __init__(self, path: Path, auth_env: Mapping[str, str]) -> None:
        self._path = path
        self._auth_env = dict(auth_env)

    @property
    def path(self) -> Path:
        return self._path

    def _env(self) -> dict[str, str]:
        """继承进程环境，叠加认证变量。

        Repo 不关心认证是 SSH 还是 HTTPS——gitauth 已经把差异吸收掉了。
        """
        env = os.environ.copy()
        env.update(self._auth_env)
        return env

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self._path), *args],
            capture_output=True,
            text=True,
            check=check,
            env=self._env(),
        )

    def init(self, url: str, branch: str) -> None:
        """确保工作副本就绪。

        远端不可达时抛 RemoteUnavailableError，且不自动创建远端仓库——
        那需要比 Deploy Key 更高的权限，与最小权限原则冲突。
        """
        if (self._path / ".git").is_dir():
            self._reconcile_origin(url)
            return

        probe = subprocess.run(
            ["git", "ls-remote", url],
            capture_output=True, text=True, env=self._env(),
        )
        if probe.returncode != 0:
            raise RemoteUnavailableError(
                f"Cannot reach remote repository {url}. Check that it exists "
                "and that the credentials have write access."
                f" git output: {probe.stderr.strip()}"
            )

        self._path.mkdir(parents=True, exist_ok=True)

        clone = subprocess.run(
            ["git", "clone", "--quiet", "--branch", branch, url, str(self._path)],
            capture_output=True, text=True, env=self._env(),
        )
        if clone.returncode == 0:
            _LOGGER.info("Cloned working copy from remote")
            return

        # 远端可达但没有该分支，即空仓库。
        _LOGGER.info("Remote is empty, initialising a new working copy")
        subprocess.run(
            ["git", "init", "-q", str(self._path)], check=True, capture_output=True
        )
        # 在尚无任何提交的仓库上设定默认分支。symbolic-ref 在所有 git
        # 版本上都有效，比依赖 `git init -b`（需 2.28+）更稳。
        self._run("symbolic-ref", "HEAD", f"refs/heads/{branch}")
        self._run("remote", "add", "origin", url)

    def _reconcile_origin(self, url: str) -> None:
        """把已有工作副本的 origin 校正到当前配置的地址。

        origin 是首次 init 时写进 git config 的，此后不会自动跟随配置变化。
        少了这一步，用户在 UI 改了 repo_url 后，add-on 会继续往旧仓库推送，
        而日志照着新地址打印——静默地做错事，比直接报错危险得多。

        只改 remote，不重新 clone：工作副本和本地历史都要留着。若新地址
        不可达或历史冲突，会在 push 阶段暴露为 PushError 并触发通知。
        """
        current = self._run("remote", "get-url", "origin", check=False)
        if current.returncode != 0:
            self._run("remote", "add", "origin", url)
            return

        if current.stdout.strip() != url:
            _LOGGER.info("Remote URL changed, updating origin to %s", url)
            self._run("remote", "set-url", "origin", url)

    def has_changes(self) -> bool:
        """是否有待提交的变更。

        先 add -A：未跟踪的文件只有进了暂存区才会被 --porcelain 稳定报告。
        """
        self._run("add", "-A")
        return bool(self._run("status", "--porcelain").stdout.strip())

    def show_changes(self) -> str:
        return self._run("status", "--short").stdout

    def commit(self, author_name: str, author_email: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._run("add", "-A")
        result = self._run(
            "-c", f"user.name={author_name}",
            "-c", f"user.email={author_email}",
            "commit", "-q", "-m", f"Auto backup: {stamp}",
            check=False,
        )
        if result.returncode != 0:
            raise CommitError(f"Failed to create commit: {result.stderr.strip()}")

    def push(
        self, branch: str, retry_delays: Sequence[float] = DEFAULT_RETRY_DELAYS
    ) -> None:
        """推送，失败则按 retry_delays 退避重试。用尽后抛 PushError。"""
        # None 代表首次尝试（不休眠），其后每个元素是一次重试前的等待秒数。
        attempts: list[float | None] = [None, *retry_delays]
        last_error = ""

        for delay in attempts:
            if delay is not None:
                _LOGGER.warning("Push failed, retrying in %ss", delay)
                time.sleep(delay)

            result = self._run("push", "-q", "origin", f"HEAD:{branch}", check=False)
            if result.returncode == 0:
                return
            last_error = result.stderr.strip()

        raise PushError(f"Push failed, all retries exhausted: {last_error}")
