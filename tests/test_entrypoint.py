"""容器入口的回归测试。

真实故障（2026-07-20 首次部署）：Dockerfile 里声明的 `ENV PYTHONPATH=/opt/hacgb`
在容器中并不生效——s6-overlay 把容器环境变量存进 /run/s6/container_environment/，
只有走 `with-contenv` 的服务才读得到，而 CMD 是作为 legacy service 拉起的。
结果 `python3 -m hacgb` 直接报 `No module named hacgb`，add-on 起不来。

因此入口必须不依赖任何环境变量。本测试用**刻意不含 PYTHONPATH** 的干净环境
运行真实启动器，把这个坑钉死。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = REPO_ROOT / "ha_config_git_backup/rootfs/opt/hacgb/run.py"


def test_launcher_exists():
    """入口必须是一个可直接用绝对路径运行的脚本。

    用绝对路径运行时 Python 会把脚本所在目录放进 sys.path[0]，
    因而无需 PYTHONPATH——这正是修复的关键。
    """
    assert LAUNCHER.is_file(), f"启动器不存在：{LAUNCHER}"


def test_launcher_runs_without_pythonpath(tmp_path: Path, exclude_file: Path):
    """在没有 PYTHONPATH 的环境里，启动器应能完成一轮备份。"""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)

    config = tmp_path / "config"
    config.mkdir()
    (config / "configuration.yaml").write_text("default_config:\n", encoding="utf-8")

    ssh = tmp_path / "ssh"
    ssh.mkdir()
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "test",
         "-f", str(ssh / "id_ed25519"), "-q"],
        check=True,
    )

    options = tmp_path / "options.json"
    options.write_text(
        '{"repo_url":"%s","branch":"main","interval":1,'
        '"commit_author_name":"Test Bot","commit_author_email":"bot@example.com",'
        '"dry_run":false,"notify_on_failure":false}' % remote,
        encoding="utf-8",
    )

    # 刻意构造一个不含 PYTHONPATH 的环境，复现容器里的真实条件。
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "HACGB_OPTIONS": str(options),
        "HACGB_SSH_DIR": str(ssh),
        "HACGB_REPO_DIR": str(tmp_path / "repo"),
        "HACGB_SOURCE_DIR": str(config),
        "HACGB_DEFAULT_EXCLUDES": str(exclude_file),
        "HACGB_EXCLUDE_FILE": str(tmp_path / "merged-exclude"),
        "HACGB_RUN_ONCE": "true",
    }
    assert "PYTHONPATH" not in env

    result = subprocess.run(
        [sys.executable, "-u", str(LAUNCHER)],
        env=env, capture_output=True, text=True,
    )

    assert result.returncode == 0, (
        f"启动器退出码 {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "Backup pushed to main" in result.stdout, result.stdout

    landed = subprocess.run(
        ["git", "-C", str(remote), "log", "-1", "--format=%s", "main"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert landed.startswith("Auto backup: ")


def test_dockerfile_does_not_rely_on_pythonpath():
    """Dockerfile 不得再用 ENV 指令定位包——它在 s6 下无效。

    只看真正的指令行，不看注释：注释里提到 PYTHONPATH 是在解释这个坑，
    那是要保留的。
    """
    dockerfile = (REPO_ROOT / "ha_config_git_backup/Dockerfile").read_text(
        encoding="utf-8"
    )
    instructions = [
        line.strip()
        for line in dockerfile.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert not any(
        line.upper().startswith("ENV") and "PYTHON" in line.upper()
        for line in instructions
    ), f"Dockerfile 仍在用 ENV 传 Python 配置：{instructions}"

    cmd_lines = [line for line in instructions if line.upper().startswith("CMD")]
    assert len(cmd_lines) == 1
    assert "/opt/hacgb/run.py" in cmd_lines[0]
    # -u 取代被剥离的 PYTHONUNBUFFERED，否则日志会卡在缓冲区里。
    assert '"-u"' in cmd_lines[0]


def test_empty_repo_url_fails_fast(tmp_path: Path, exclude_file: Path):
    """未配置 repo_url 时必须立刻报错，而不是默默推到某个地方。"""
    options = tmp_path / "options.json"
    options.write_text('{"repo_url":"","notify_on_failure":false}', encoding="utf-8")

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "HACGB_OPTIONS": str(options),
        "HACGB_SSH_DIR": str(tmp_path / "ssh"),
        "HACGB_REPO_DIR": str(tmp_path / "repo"),
        "HACGB_SOURCE_DIR": str(tmp_path),
        "HACGB_DEFAULT_EXCLUDES": str(exclude_file),
        "HACGB_EXCLUDE_FILE": str(tmp_path / "merged"),
        "HACGB_RUN_ONCE": "true",
    }
    result = subprocess.run(
        [sys.executable, "-u", str(LAUNCHER)], env=env, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "repo_url is not configured" in (result.stdout + result.stderr)


def test_scp_style_url_is_rejected_with_guidance(tmp_path: Path, exclude_file: Path):
    options = tmp_path / "options.json"
    options.write_text(
        '{"repo_url":"git@github.com:user/repo.git","notify_on_failure":false}',
        encoding="utf-8",
    )

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "HACGB_OPTIONS": str(options),
        "HACGB_SSH_DIR": str(tmp_path / "ssh"),
        "HACGB_REPO_DIR": str(tmp_path / "repo"),
        "HACGB_SOURCE_DIR": str(tmp_path),
        "HACGB_DEFAULT_EXCLUDES": str(exclude_file),
        "HACGB_EXCLUDE_FILE": str(tmp_path / "merged"),
        "HACGB_RUN_ONCE": "true",
    }
    result = subprocess.run(
        [sys.executable, "-u", str(LAUNCHER)], env=env, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "ssh://" in (result.stdout + result.stderr)
