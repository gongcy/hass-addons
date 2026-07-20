from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from hacgb.options import Config


def test_loads_values_from_file(write_options):
    path = write_options({"branch": "develop", "interval": 3600})
    cfg = Config.load(path)
    assert cfg.branch == "develop"
    assert cfg.interval == 3600


def test_missing_key_falls_back_to_default(write_options):
    path = write_options({"branch": "develop"})
    cfg = Config.load(path)
    assert cfg.interval == 86400


def test_null_value_falls_back_to_default(write_options):
    path = write_options({"branch": None})
    cfg = Config.load(path)
    assert cfg.branch == "main"


def test_missing_file_uses_all_defaults(tmp_path: Path):
    cfg = Config.load(tmp_path / "nope.json")
    assert cfg.branch == "main"
    assert cfg.interval == 86400
    assert cfg.dry_run is False


def test_false_is_a_real_value_not_a_missing_one(write_options):
    """dry_run=false 必须保持 false，不能被当成缺失而回退到默认值。"""
    path = write_options({"dry_run": False})
    cfg = Config.load(path)
    assert cfg.dry_run is False


def test_true_dry_run_is_read(write_options):
    path = write_options({"dry_run": True})
    cfg = Config.load(path)
    assert cfg.dry_run is True


def test_interval_is_coerced_to_int(write_options):
    path = write_options({"interval": "7200"})
    cfg = Config.load(path)
    assert cfg.interval == 7200
    assert isinstance(cfg.interval, int)


def test_config_is_immutable(write_options):
    path = write_options({})
    cfg = Config.load(path)
    with pytest.raises(FrozenInstanceError):
        cfg.branch = "other"  # type: ignore[misc]


def test_malformed_json_uses_defaults(options_file: Path):
    options_file.write_text("{not json", encoding="utf-8")
    cfg = Config.load(options_file)
    assert cfg.branch == "main"


def test_repo_url_defaults_to_empty(tmp_path: Path):
    """公开发布后不能有默认仓库地址。

    原实现默认指向作者的仓库，别人装上不配置就启动会把自己的配置
    推向一个陌生地址。
    """
    cfg = Config.load(tmp_path / "nope.json")
    assert cfg.repo_url == ""


def test_defaults_embed_no_real_host(tmp_path: Path):
    """默认值里不得内置任何真实主机。

    同样用通用模式而不是列举已知域名——列举会把域名写进代码，
    且只挡得住列举到的那一个。
    """
    import re

    cfg = Config.load(tmp_path / "nope.json")

    assert cfg.repo_url == ""
    assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", cfg.commit_author_email)
    # 作者邮箱的域名必须是通用占位，不能指向任何真实主机。
    assert cfg.commit_author_email.endswith("@local")


def test_username_defaults_to_oauth2(tmp_path: Path):
    assert Config.load(tmp_path / "nope.json").username == "oauth2"


def test_token_defaults_to_empty(tmp_path: Path):
    assert Config.load(tmp_path / "nope.json").token == ""


def test_host_key_defaults_to_empty(tmp_path: Path):
    assert Config.load(tmp_path / "nope.json").host_key == ""


def test_exclude_defaults_to_empty(tmp_path: Path):
    assert Config.load(tmp_path / "nope.json").exclude == ()


def test_exclude_is_read_as_tuple(write_options):
    path = write_options({"exclude": ["/a/", "*.bak"]})
    cfg = Config.load(path)
    assert cfg.exclude == ("/a/", "*.bak")


def test_exclude_non_list_falls_back_to_empty(write_options):
    """UI 或手改 options.json 可能塞进非列表值，不能让它炸掉启动。"""
    path = write_options({"exclude": "not-a-list"})
    assert Config.load(path).exclude == ()


def test_token_is_read(write_options):
    path = write_options({"token": "ghp_example"})
    assert Config.load(path).token == "ghp_example"


def test_host_key_is_read(write_options):
    line = "[git.example.com]:2222 ssh-ed25519 AAAA"
    path = write_options({"host_key": line})
    assert Config.load(path).host_key == line
