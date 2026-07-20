"""所有测试共用的 fixture。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def options_file(tmp_path: Path) -> Path:
    """指向一个尚未创建的 options.json 路径。"""
    return tmp_path / "options.json"


@pytest.fixture
def write_options(options_file: Path):
    """把 dict 写成 options.json 并返回其路径。"""

    def _write(data: dict) -> Path:
        options_file.write_text(json.dumps(data), encoding="utf-8")
        return options_file

    return _write


@pytest.fixture
def ssh_dir(tmp_path: Path) -> Path:
    return tmp_path / "ssh"


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """仿真的 HA 配置目录。"""
    d = tmp_path / "config"
    d.mkdir()
    return d


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    return tmp_path / "repo"


@pytest.fixture
def remote_repo(tmp_path: Path) -> Path:
    """本地 bare 仓库，充当远端。测试因此完全不依赖网络。"""
    d = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(d)], check=True)
    return d


@pytest.fixture
def exclude_file() -> Path:
    """真实的排除表，测试和运行时用同一份。"""
    root = Path(__file__).resolve().parent.parent
    return root / "ha_config_git_backup/rootfs/etc/hacgb/backup-exclude"
