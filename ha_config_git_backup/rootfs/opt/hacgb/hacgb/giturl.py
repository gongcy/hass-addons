"""解析 repo_url，判定认证方式。

只拒绝 scp 短语法（git@host:path）：它无法表达非标准端口，会静默退回 22，
是实践中反复咬人的陷阱。其余形式一律放行交给 git——这样既支持本地 bare
仓库，也不必预判 git 支持的全部协议。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

from .errors import InvalidRepoUrlError

# user@host:path —— 冒号后不是数字端口，即 scp 短语法。
_SCP_SYNTAX = re.compile(r"^[^/:]+@[^/:]+:(?!\d+/)")


class Scheme(Enum):
    """认证方式由协议决定。"""

    SSH = "ssh"
    HTTPS = "https"
    LOCAL = "local"


@dataclass(frozen=True)
class GitUrl:
    scheme: Scheme
    host: str
    port: int | None


def parse_git_url(url: str) -> GitUrl:
    """解析 URL，无法安全处理时抛 InvalidRepoUrlError。"""
    url = url.strip()

    if not url:
        raise InvalidRepoUrlError(
            "repo_url is not configured. Set it to a full URL such as "
            "ssh://git@github.com/user/repo.git or "
            "https://github.com/user/repo.git"
        )

    if _SCP_SYNTAX.match(url):
        raise InvalidRepoUrlError(
            f"scp-style URLs are not supported: {url}. They cannot express a "
            "non-standard port and silently fall back to port 22. Use "
            "ssh://git@host:port/path.git instead."
        )

    parts = urlsplit(url)

    if parts.scheme == "ssh":
        return GitUrl(Scheme.SSH, parts.hostname or "", parts.port)
    if parts.scheme in ("https", "http"):
        return GitUrl(Scheme.HTTPS, parts.hostname or "", parts.port)

    # file:// 与裸路径都当本地仓库处理。
    return GitUrl(Scheme.LOCAL, "", None)
