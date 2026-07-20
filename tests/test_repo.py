import shutil
import subprocess
from pathlib import Path

import pytest

from hacgb.errors import PushError, RemoteUnavailableError
from hacgb.repo import Repo


@pytest.fixture
def repo(repo_dir: Path) -> Repo:
    # 远端是本地路径，不走 SSH，因此不需要任何认证变量。
    return Repo(repo_dir, auth_env={"GIT_TERMINAL_PROMPT": "0"})


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_init_creates_working_copy_for_empty_remote(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    assert (repo_dir / ".git").is_dir()


def test_init_sets_origin(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    assert _git(repo_dir, "remote", "get-url", "origin") == str(remote_repo)


def test_init_sets_requested_branch_on_empty_remote(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    head = (repo_dir / ".git/HEAD").read_text(encoding="utf-8").strip()
    assert head == "ref: refs/heads/main"


def test_init_is_idempotent(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "marker.txt").write_text("keep me")
    repo.init(str(remote_repo), "main")
    assert (repo_dir / "marker.txt").exists()


def test_init_updates_origin_when_url_changed(repo, remote_repo, repo_dir, tmp_path: Path):
    """改了 repo_url 就必须改到 origin 上。

    真机故障（2026-07-20）：工作副本已存在时 init 直接幂等返回，origin 仍是
    首次写入的旧地址。用户在 UI 改了仓库地址，add-on 却继续往旧仓库推，
    日志还照着新地址打印——静默地做错事，比报错危险得多。
    """
    repo.init(str(remote_repo), "main")

    moved = tmp_path / "moved.git"
    subprocess.run(["git", "init", "-q", "--bare", str(moved)], check=True)
    repo.init(str(moved), "main")

    assert _git(repo_dir, "remote", "get-url", "origin") == str(moved)


def test_init_keeps_working_copy_when_url_changed(repo, remote_repo, repo_dir, tmp_path: Path):
    """换地址只改 remote，不重新 clone——工作副本和历史都要留着。"""
    repo.init(str(remote_repo), "main")
    (repo_dir / "marker.txt").write_text("keep me")

    moved = tmp_path / "moved.git"
    subprocess.run(["git", "init", "-q", "--bare", str(moved)], check=True)
    repo.init(str(moved), "main")

    assert (repo_dir / "marker.txt").exists()


def test_init_raises_when_remote_missing(repo, tmp_path: Path):
    with pytest.raises(RemoteUnavailableError):
        repo.init(str(tmp_path / "nonexistent.git"), "main")


def test_no_changes_on_fresh_copy(repo, remote_repo):
    repo.init(str(remote_repo), "main")
    assert repo.has_changes() is False


def test_new_file_is_a_change(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    assert repo.has_changes() is True


def test_commit_uses_given_author(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    repo.commit("Test Bot", "bot@example.com")
    assert _git(repo_dir, "log", "-1", "--format=%an <%ae>") == "Test Bot <bot@example.com>"


def test_commit_message_has_expected_prefix(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    repo.commit("Test Bot", "bot@example.com")
    assert _git(repo_dir, "log", "-1", "--format=%s").startswith("Auto backup: ")


def test_push_lands_on_remote(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    repo.commit("Test Bot", "bot@example.com")
    repo.push("main", retry_delays=())
    assert _git(remote_repo, "log", "-1", "--format=%s", "main").startswith("Auto backup: ")


def test_push_raises_after_exhausting_retries(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    repo.commit("Test Bot", "bot@example.com")
    shutil.rmtree(remote_repo)
    with pytest.raises(PushError):
        repo.push("main", retry_delays=(0, 0))


def test_push_actually_retries_before_giving_up(repo, remote_repo, repo_dir, monkeypatch):
    """确认重试真的发生了，而不是失败一次就放弃。"""
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    repo.commit("Test Bot", "bot@example.com")
    shutil.rmtree(remote_repo)

    slept: list[float] = []
    monkeypatch.setattr("hacgb.repo.time.sleep", lambda s: slept.append(s))

    with pytest.raises(PushError):
        repo.push("main", retry_delays=(10, 30))
    assert slept == [10, 30]


def test_no_changes_right_after_commit(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    repo.commit("Test Bot", "bot@example.com")
    assert repo.has_changes() is False


def test_deletion_counts_as_change(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    repo.commit("Test Bot", "bot@example.com")
    (repo_dir / "new.yaml").unlink()
    assert repo.has_changes() is True


def test_show_changes_lists_pending_files(repo, remote_repo, repo_dir):
    repo.init(str(remote_repo), "main")
    (repo_dir / "new.yaml").write_text("x")
    assert "new.yaml" in repo.show_changes()
