"""异常层次。

用异常而不是返回码表达失败：一轮备份可能因同步、初始化、提交、推送
四个环节中的任何一个而失败，调用方需要区分它们才能给出有用的诊断。
"""

from __future__ import annotations


class BackupError(Exception):
    """本 add-on 所有预期内失败的基类。"""


class SyncError(BackupError):
    """从 HA 配置目录同步到工作副本失败。"""


class RemoteUnavailableError(BackupError):
    """远端仓库不存在、不可达，或 Deploy Key 无权限。"""


class CommitError(BackupError):
    """创建 git 提交失败。"""


class PushError(BackupError):
    """推送到远端失败，且已用尽重试。"""


class InvalidRepoUrlError(BackupError):
    """repo_url 为空或格式不受支持。"""
