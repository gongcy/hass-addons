"""add-on 入口：读配置、校验、自举、进入主循环。"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from .backup import BackupJob
from .containerenv import read_container_env
from .errors import BackupError, InvalidRepoUrlError, RemoteUnavailableError
from .excludes import build_exclude_file
from .gitauth import build_auth_env
from .giturl import Scheme, parse_git_url
from .notify import Notifier
from .options import Config
from .repo import Repo
from .sshkeys import SshKeys

_LOGGER = logging.getLogger("hacgb")

OPTIONS_PATH = Path(os.environ.get("HACGB_OPTIONS", "/data/options.json"))
SSH_DIR = Path(os.environ.get("HACGB_SSH_DIR", "/data/ssh"))
REPO_DIR = Path(os.environ.get("HACGB_REPO_DIR", "/data/repo"))
# 注意是 /homeassistant 而非 /config——见 config.yaml 中的 map 配置。
SOURCE_DIR = Path(os.environ.get("HACGB_SOURCE_DIR", "/homeassistant"))
DEFAULT_EXCLUDES = Path(
    os.environ.get("HACGB_DEFAULT_EXCLUDES", "/etc/hacgb/backup-exclude")
)
EXCLUDE_FILE = Path(os.environ.get("HACGB_EXCLUDE_FILE", "/data/backup-exclude"))
SUPERVISOR_URL = os.environ.get("HACGB_SUPERVISOR_URL", "http://supervisor")

# 等待用户操作时的休眠间隔。不退出进程，避免 Supervisor 反复重启刷屏。
_IDLE_SECONDS = 3600


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stdout,
    )


def _idle_forever() -> int:
    while True:
        time.sleep(_IDLE_SECONDS)


def main() -> int:
    _configure_logging()
    # 供测试与手工验证驱动单轮执行；正常运行时不设此变量。
    run_once = os.environ.get("HACGB_RUN_ONCE") == "true"

    config = Config.load(OPTIONS_PATH)
    notifier = Notifier(
        SUPERVISOR_URL,
        read_container_env("SUPERVISOR_TOKEN"),
        enabled=config.notify_on_failure,
    )

    _LOGGER.info("HA Config Git Backup starting")

    # 先校验 URL：配错了就没必要生成密钥、建工作副本。
    try:
        url = parse_git_url(config.repo_url)
    except InvalidRepoUrlError as err:
        _LOGGER.error("%s", err)
        notifier.failure(str(err))
        return 1 if run_once else _idle_forever()

    _LOGGER.info(
        "Repository %s branch %s interval %ss dry_run=%s",
        config.repo_url, config.branch, config.interval, config.dry_run,
    )

    exclude_file = build_exclude_file(config.exclude, DEFAULT_EXCLUDES, EXCLUDE_FILE)

    keys = SshKeys(SSH_DIR)
    if url.scheme is Scheme.SSH:
        keys.write_known_hosts(config.host_key)
        # 密钥是本次新生成的：用户还没配 Deploy Key，此时推送必然失败。
        # 打印公钥和操作指引后进入等待，而不是反复失败刷屏。
        if keys.ensure():
            _LOGGER.info("Generated a new SSH key pair.")
            _LOGGER.info("Add the following public key as a deploy key with")
            _LOGGER.info("write access, then restart this add-on:")
            _LOGGER.info("")
            _LOGGER.info("%s", keys.public_key())
            _LOGGER.info("")
            return 0 if run_once else _idle_forever()

    auth_env = build_auth_env(
        url, keys, config.username, config.token, config.host_key
    )
    repo = Repo(REPO_DIR, auth_env)

    try:
        repo.init(config.repo_url, config.branch)
    except RemoteUnavailableError as err:
        _LOGGER.error("%s", err)
        notifier.failure(
            f"Cannot reach {config.repo_url}. Check that the repository "
            "exists and the credentials have write access."
        )
        return 1 if run_once else _idle_forever()

    job = BackupJob(
        config=config, source_dir=SOURCE_DIR, repo=repo, exclude_file=exclude_file
    )

    while True:
        try:
            job.run_once()
        except BackupError as err:
            _LOGGER.error("Backup run failed: %s", err)
            notifier.failure(str(err))
        if run_once:
            return 0
        time.sleep(config.interval)


if __name__ == "__main__":
    raise SystemExit(main())
