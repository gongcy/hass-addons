"""合并内置默认排除表与用户配置。

用户规则是"追加"而非"替换"：内置默认值（数据库、日志、缓存、纯运行时状态）
始终生效。不提供关闭开关——新手误关会把 GB 级数据库推进仓库。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

_LOGGER = logging.getLogger(__name__)

# 无论用户怎么配都必须排除的条目。
# /.git/ 若被移除，rsync --delete 会删光工作副本的 git 元数据，
# 每轮退化成全新仓库、历史丢失。这条不能交给配置。
MANDATORY_EXCLUDES: tuple[str, ...] = ("/.git/",)


def build_exclude_file(
    user_excludes: Sequence[str], defaults_path: Path, dest: Path
) -> Path:
    """写出最终排除表，返回 dest。

    顺序：强制项 → 内置默认值 → 用户追加项。
    强制项排在最前面，因为 rsync 按顺序匹配。
    """
    lines: list[str] = list(MANDATORY_EXCLUDES)

    try:
        defaults = defaults_path.read_text(encoding="utf-8").splitlines()
    except OSError as err:
        _LOGGER.warning("Built-in exclude list unreadable (%s): %s", defaults_path, err)
        defaults = []
    lines.extend(defaults)

    cleaned = [entry.strip() for entry in user_excludes]
    lines.extend(entry for entry in cleaned if entry)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest
