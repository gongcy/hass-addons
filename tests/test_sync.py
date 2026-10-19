from pathlib import Path

import pytest

from hacgb.errors import SyncError
from hacgb.sync import sync_config


@pytest.fixture
def populated_config(config_dir: Path) -> Path:
    """仿真的 HA 配置目录，覆盖保留项与各类排除项。"""
    (config_dir / ".storage").mkdir()
    (config_dir / ".storage/core.restore_state").write_text("runtime state")
    (config_dir / ".storage/bluetooth.passive_update_processor").write_text("bt cache")
    (config_dir / ".storage/core.device_registry").write_text('{"devices":[]}')
    (config_dir / "tts").mkdir()
    (config_dir / ".cloud").mkdir()
    (config_dir / "deps").mkdir()
    (config_dir / "custom_components/foo/__pycache__").mkdir(parents=True)

    (config_dir / "configuration.yaml").write_text("default_config:\n")
    (config_dir / "secrets.yaml").write_text("token: abc123\n")
    (config_dir / ".storage/core.config").write_text('{"k":"v"}')
    (config_dir / "home-assistant_v2.db").write_text("db")
    (config_dir / "home-assistant_v2.db-wal").write_text("wal")
    (config_dir / "home-assistant.log").write_text("log")
    (config_dir / "tts/cached.mp3").write_text("audio")
    (config_dir / ".cloud/prefs").write_text("creds")
    (config_dir / "deps/pkg").write_text("dep")
    (config_dir / "custom_components/foo/__pycache__/x.pyc").write_text("pyc")
    return config_dir


def test_yaml_config_is_copied(populated_config, repo_dir, exclude_file):
    sync_config(populated_config, repo_dir, exclude_file)
    assert (repo_dir / "configuration.yaml").exists()


def test_secrets_and_storage_are_included_by_design(
    populated_config, repo_dir, exclude_file
):
    """按设计选择全量备份，这两项必须在内。"""
    sync_config(populated_config, repo_dir, exclude_file)
    assert (repo_dir / "secrets.yaml").exists()
    assert (repo_dir / ".storage/core.config").exists()


def test_pure_runtime_state_is_excluded(populated_config, repo_dir, exclude_file):
    """.storage 里的纯运行时状态排除掉。

    实测这两个文件每几分钟就被 HA 重写一次（core.restore_state 单个就有
    294KB），若入库则"无变更跳过"几乎永不触发，git log 会被噪声淹没。
    它们只是实体最后已知值和蓝牙缓存，恢复价值近乎为零。
    """
    sync_config(populated_config, repo_dir, exclude_file)
    assert not (repo_dir / ".storage/core.restore_state").exists()
    assert not (repo_dir / ".storage/bluetooth.passive_update_processor").exists()


def test_storage_registries_are_kept(populated_config, repo_dir, exclude_file):
    """注册表类文件必须保留——灾难恢复时真正需要的就是它们。"""
    sync_config(populated_config, repo_dir, exclude_file)
    assert (repo_dir / ".storage/core.device_registry").exists()


def test_database_and_sidecars_are_excluded(populated_config, repo_dir, exclude_file):
    sync_config(populated_config, repo_dir, exclude_file)
    assert not (repo_dir / "home-assistant_v2.db").exists()
    assert not (repo_dir / "home-assistant_v2.db-wal").exists()


def test_logs_caches_and_cloud_creds_are_excluded(
    populated_config, repo_dir, exclude_file
):
    sync_config(populated_config, repo_dir, exclude_file)
    assert not (repo_dir / "home-assistant.log").exists()
    assert not (repo_dir / "tts").exists()
    assert not (repo_dir / "deps").exists()
    assert not (repo_dir / ".cloud").exists()


def test_pycache_is_excluded_at_any_depth(populated_config, repo_dir, exclude_file):
    sync_config(populated_config, repo_dir, exclude_file)
    assert (repo_dir / "custom_components/foo").exists()
    assert not (repo_dir / "custom_components/foo/__pycache__").exists()


def test_deletions_propagate(populated_config, repo_dir, exclude_file):
    sync_config(populated_config, repo_dir, exclude_file)
    assert (repo_dir / "configuration.yaml").exists()
    (populated_config / "configuration.yaml").unlink()
    sync_config(populated_config, repo_dir, exclude_file)
    assert not (repo_dir / "configuration.yaml").exists()


def test_git_metadata_survives_sync(populated_config, repo_dir, exclude_file):
    """最关键的一条：--delete 绝不能吃掉工作副本的 .git 目录。"""
    (repo_dir / ".git").mkdir(parents=True)
    (repo_dir / ".git/HEAD").write_text("ref: refs/heads/main")
    sync_config(populated_config, repo_dir, exclude_file)
    assert (repo_dir / ".git/HEAD").read_text() == "ref: refs/heads/main"


def test_git_metadata_survives_when_dest_has_excluded_files(
    populated_config, repo_dir, exclude_file
):
    """--delete-excluded 会清理接收端的排除项，.git 必须靠 protect 规则保住。"""
    (repo_dir / ".git").mkdir(parents=True)
    (repo_dir / ".git/HEAD").write_text("ref: refs/heads/main")
    (repo_dir / "home-assistant.log").write_text("stale log")
    sync_config(populated_config, repo_dir, exclude_file)
    assert (repo_dir / ".git/HEAD").read_text() == "ref: refs/heads/main"
    assert not (repo_dir / "home-assistant.log").exists()


def test_newly_excluded_files_are_removed_from_working_copy(
    populated_config, repo_dir, tmp_path: Path
):
    """先入库、后加进排除表的文件要从工作副本删掉，而不是以旧内容冻结。"""
    rules = tmp_path / "rules"
    rules.write_text("/.git/\n")
    sync_config(populated_config, repo_dir, rules)
    assert (repo_dir / "secrets.yaml").exists()

    rules.write_text("/.git/\n/secrets.yaml\n")
    sync_config(populated_config, repo_dir, rules)
    assert not (repo_dir / "secrets.yaml").exists()
    assert (populated_config / "secrets.yaml").exists()


def test_missing_source_raises(tmp_path: Path, repo_dir, exclude_file):
    with pytest.raises(SyncError):
        sync_config(tmp_path / "nope", repo_dir, exclude_file)


def test_missing_exclude_file_raises(populated_config, repo_dir, tmp_path: Path):
    with pytest.raises(SyncError):
        sync_config(populated_config, repo_dir, tmp_path / "nope")
