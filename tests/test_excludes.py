from pathlib import Path

import pytest

from hacgb.excludes import MANDATORY_EXCLUDES, build_exclude_file


@pytest.fixture
def defaults(tmp_path: Path) -> Path:
    p = tmp_path / "defaults"
    p.write_text(
        "# builtin defaults\n"
        "/home-assistant_v2.db\n"
        "*.log\n"
        "/.cloud/\n",
        encoding="utf-8",
    )
    return p


def test_builtin_defaults_are_kept(defaults, tmp_path: Path):
    out = build_exclude_file([], defaults, tmp_path / "out")
    text = out.read_text(encoding="utf-8")
    assert "/home-assistant_v2.db" in text
    assert "*.log" in text
    assert "/.cloud/" in text


def test_user_entries_are_appended(defaults, tmp_path: Path):
    out = build_exclude_file(["/my_secret_dir/", "*.bak"], defaults, tmp_path / "out")
    text = out.read_text(encoding="utf-8")
    assert "/my_secret_dir/" in text
    assert "*.bak" in text


def test_user_entries_do_not_replace_defaults(defaults, tmp_path: Path):
    """追加语义：写了自己的规则不代表内置的就没了。"""
    out = build_exclude_file(["*.bak"], defaults, tmp_path / "out")
    text = out.read_text(encoding="utf-8")
    assert "*.bak" in text
    assert "/home-assistant_v2.db" in text


def test_git_metadata_is_always_excluded(defaults, tmp_path: Path):
    out = build_exclude_file([], defaults, tmp_path / "out")
    assert "/.git/" in out.read_text(encoding="utf-8")


def test_user_cannot_remove_git_exclusion(defaults, tmp_path: Path):
    """最关键的一条：用户无论写什么，/.git/ 都必须在。

    能移除它就等于允许 rsync --delete 删光工作副本的 git 元数据，
    仓库历史随之丢失。
    """
    out = build_exclude_file(["!/.git/", "- /.git/"], defaults, tmp_path / "out")
    lines = [ln.strip() for ln in out.read_text(encoding="utf-8").splitlines()]
    assert "/.git/" in lines


def test_mandatory_entries_come_first(defaults, tmp_path: Path):
    """rsync 按顺序匹配，强制项必须在最前面。"""
    out = build_exclude_file(["*.bak"], defaults, tmp_path / "out")
    lines = [ln.strip() for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines[0] == "/.git/"


def test_blank_and_whitespace_user_entries_are_dropped(defaults, tmp_path: Path):
    out = build_exclude_file(["", "   ", "*.bak"], defaults, tmp_path / "out")
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip() == ""]
    assert lines == []


def test_user_entries_are_stripped(defaults, tmp_path: Path):
    out = build_exclude_file(["  *.bak  "], defaults, tmp_path / "out")
    assert "*.bak" in [
        ln.strip() for ln in out.read_text(encoding="utf-8").splitlines()
    ]


def test_returns_destination_path(defaults, tmp_path: Path):
    dest = tmp_path / "out"
    assert build_exclude_file([], defaults, dest) == dest


def test_creates_parent_directory(defaults, tmp_path: Path):
    dest = tmp_path / "nested" / "dir" / "out"
    build_exclude_file([], defaults, dest)
    assert dest.is_file()


def test_missing_defaults_file_still_yields_mandatory(tmp_path: Path):
    """内置默认表意外缺失时也不能让 /.git/ 丢掉。"""
    out = build_exclude_file(["*.bak"], tmp_path / "nope", tmp_path / "out")
    text = out.read_text(encoding="utf-8")
    assert "/.git/" in text
    assert "*.bak" in text


def test_rewritten_not_appended_on_repeat_calls(defaults, tmp_path: Path):
    dest = tmp_path / "out"
    build_exclude_file(["*.bak"], defaults, dest)
    build_exclude_file(["*.bak"], defaults, dest)
    assert dest.read_text(encoding="utf-8").count("*.bak") == 1


def test_mandatory_excludes_constant_contains_git():
    assert "/.git/" in MANDATORY_EXCLUDES
