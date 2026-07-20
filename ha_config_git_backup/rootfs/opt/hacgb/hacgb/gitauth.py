"""按 URL 协议产出 git 所需的认证环境变量。

把认证与 git 操作解耦：Repo 只收一份环境变量，不关心凭据是怎么来的。

这些变量由本进程构造后传给 subprocess，与 s6 剥离容器环境变量的问题无关
（那个只涉及 Supervisor/Docker 注入给容器的变量）。
"""

from __future__ import annotations

from .giturl import GitUrl, Scheme
from .sshkeys import SshKeys

ASKPASS_PATH = "/opt/hacgb/askpass.sh"


def build_auth_env(
    url: GitUrl,
    ssh_keys: SshKeys,
    username: str,
    token: str,
    host_key: str,
) -> dict[str, str]:
    """产出 git 子进程所需的认证环境变量。"""
    # 容器里没人能回答交互式凭据提示，任何协议下都必须禁掉。
    env = {"GIT_TERMINAL_PROMPT": "0"}

    if url.scheme is Scheme.SSH:
        env["GIT_SSH_COMMAND"] = ssh_keys.git_ssh_command(
            strict=bool(host_key and host_key.strip())
        )
    elif url.scheme is Scheme.HTTPS:
        # token 只经 askpass 传递，绝不拼进 remote URL——那会把它写进
        # .git/config 并带进 git 的报错输出。
        env["GIT_ASKPASS"] = ASKPASS_PATH
        env["HACGB_GIT_USERNAME"] = username
        env["HACGB_GIT_PASSWORD"] = token

    return env
