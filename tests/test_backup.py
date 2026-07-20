import subprocess
from pathlib import Path

import pytest

from hacgb.backup import BackupJob, Outcome
from hacgb.errors import SyncError
from hacgb.options import Config
from hacgb.repo import Repo


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True
    )


def _make_job(config_dir, repo_dir, remote_repo, exclude_file, **overrides) -> BackupJob:
    # 先合并再构造。若把默认值直接写在 Config(...) 里再展开 **overrides，
    # 调用方传 dry_run=True 会撞上"重复关键字参数"而报 TypeError。
    settings = {
        "repo_url": str(remote_repo),
        "branch": "main",
        "interval": 1,
        "commit_author_name": "Test Bot",
        "commit_author_email": "bot@example.com",
        "dry_run": False,
        "notify_on_failure": False,
    }
    settings.update(overrides)
    cfg = Config(**settings)
    repo = Repo(repo_dir, auth_env={"GIT_TERMINAL_PROMPT": "0"})
    repo.init(cfg.repo_url, cfg.branch)
    return BackupJob(
        config=cfg, source_dir=config_dir, repo=repo, exclude_file=exclude_file
    )


@pytest.fixture
def job(config_dir: Path, repo_dir: Path, remote_repo: Path, exclude_file: Path):
    """一个连好本地假远端、可直接跑的备份任务。"""
    (config_dir / "configuration.yaml").write_text("default_config:\n")
    return _make_job(config_dir, repo_dir, remote_repo, exclude_file)


def test_first_run_pushes(job):
    assert job.run_once() is Outcome.PUSHED


def test_pushed_content_reaches_remote(job, remote_repo):
    job.run_once()
    files = _git(remote_repo, "ls-tree", "--name-only", "main").stdout
    assert "configuration.yaml" in files


def test_second_run_without_changes_is_a_noop(job):
    job.run_once()
    assert job.run_once() is Outcome.NO_CHANGES


def test_changed_config_produces_new_commit(job, config_dir, remote_repo):
    job.run_once()
    first = _git(remote_repo, "rev-parse", "main").stdout.strip()

    (config_dir / "configuration.yaml").write_text("default_config:\n# changed\n")
    assert job.run_once() is Outcome.PUSHED

    second = _git(remote_repo, "rev-parse", "main").stdout.strip()
    assert first != second


def test_dry_run_does_not_push(config_dir, repo_dir, remote_repo, exclude_file):
    (config_dir / "configuration.yaml").write_text("default_config:\n")
    job = _make_job(config_dir, repo_dir, remote_repo, exclude_file, dry_run=True)

    assert job.run_once() is Outcome.DRY_RUN
    # 远端仍然没有 main 分支。
    assert _git(remote_repo, "rev-parse", "main").returncode != 0


def test_missing_source_raises_sync_error(
    tmp_path: Path, repo_dir, remote_repo, exclude_file
):
    cfg = Config(repo_url=str(remote_repo), branch="main")
    repo = Repo(repo_dir, auth_env={"GIT_TERMINAL_PROMPT": "0"})
    repo.init(cfg.repo_url, cfg.branch)
    job = BackupJob(
        config=cfg,
        source_dir=tmp_path / "nope",
        repo=repo,
        exclude_file=exclude_file,
    )
    with pytest.raises(SyncError):
        job.run_once()


def test_deletion_propagates_to_remote(job, config_dir, remote_repo):
    (config_dir / "temp.yaml").write_text("x")
    job.run_once()
    (config_dir / "temp.yaml").unlink()
    job.run_once()

    files = _git(remote_repo, "ls-tree", "--name-only", "main").stdout
    assert "temp.yaml" not in files
