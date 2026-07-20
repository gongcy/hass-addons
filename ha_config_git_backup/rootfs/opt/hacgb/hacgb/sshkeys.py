"""SSH 密钥自举与主机指纹管理。

面向任意 git 主机，无法预置指纹，因此默认走 TOFU
（StrictHostKeyChecking=accept-new）：首次连接记录，此后变更即拒绝——
这就是 SSH 的标准行为。用户填了 host_key 则切换为严格模式。

任何情况下都不使用 StrictHostKeyChecking=no：那等于完全放弃中间人防护。
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


class SshKeys:
    """管理 add-on 持久卷中的 SSH 身份。"""

    def __init__(self, ssh_dir: Path) -> None:
        self._dir = ssh_dir

    @property
    def private_key(self) -> Path:
        return self._dir / "id_ed25519"

    @property
    def known_hosts(self) -> Path:
        return self._dir / "known_hosts"

    def ensure(self) -> bool:
        """确保密钥对存在。

        返回 True 表示本次新生成——此时用户尚未配置 Deploy Key，
        调用方应打印公钥并等待，而不是让推送反复失败。
        """
        self._dir.mkdir(parents=True, exist_ok=True)
        self._dir.chmod(0o700)

        if self.private_key.exists():
            self.private_key.chmod(0o600)
            return False

        subprocess.run(
            [
                "ssh-keygen",
                "-t", "ed25519",
                "-N", "",
                "-C", "ha-config-git-backup",
                "-f", str(self.private_key),
            ],
            check=True,
            capture_output=True,
        )
        self.private_key.chmod(0o600)
        _LOGGER.info("Generated a new ed25519 key pair")
        return True

    def write_known_hosts(self, host_key: str | None = None) -> None:
        """准备 known_hosts。

        给了 host_key 就写入并覆盖旧内容；没给则只确保文件存在——
        已有内容必须保留，否则 TOFU 上一轮学到的指纹会被清掉，形同虚设。
        """
        self._dir.mkdir(parents=True, exist_ok=True)

        if host_key and host_key.strip():
            self.known_hosts.write_text(host_key.strip() + "\n", encoding="utf-8")
        elif not self.known_hosts.exists():
            self.known_hosts.write_text("", encoding="utf-8")

        self.known_hosts.chmod(0o644)

    def git_ssh_command(self, strict: bool) -> str:
        """供 GIT_SSH_COMMAND 使用的命令串。

        strict=True 用于用户显式钉住了 host_key 的场景；
        否则 accept-new（TOFU）。绝不使用 no。
        """
        policy = "yes" if strict else "accept-new"
        return (
            f"ssh -i {self.private_key}"
            f" -o UserKnownHostsFile={self.known_hosts}"
            f" -o StrictHostKeyChecking={policy}"
            " -o IdentitiesOnly=yes"
            " -o BatchMode=yes"
        )

    def public_key(self) -> str:
        return (self._dir / "id_ed25519.pub").read_text(encoding="utf-8").strip()
