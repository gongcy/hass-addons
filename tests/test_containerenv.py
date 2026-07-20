"""容器环境变量读取的测试。

真实故障（2026-07-20 部署验证）：Supervisor 注入的 SUPERVISOR_TOKEN 在 CMD
进程里读不到，失败通知因此永远发不出去——那张"防止备份静默停工数月"的
安全网一直是失效的。根因与 PYTHONPATH 丢失相同：s6-overlay 把容器环境变量
存进 /run/s6/container_environment/，只有 with-contenv 服务才读得到。
"""

from __future__ import annotations

from pathlib import Path

from hacgb.containerenv import read_container_env


def test_prefers_process_environment(tmp_path: Path):
    (tmp_path / "TOKEN").write_text("from-s6", encoding="utf-8")
    value = read_container_env("TOKEN", environ={"TOKEN": "from-process"}, s6_dir=tmp_path)
    assert value == "from-process"


def test_falls_back_to_s6_container_environment(tmp_path: Path):
    (tmp_path / "TOKEN").write_text("from-s6", encoding="utf-8")
    assert read_container_env("TOKEN", environ={}, s6_dir=tmp_path) == "from-s6"


def test_strips_trailing_newline(tmp_path: Path):
    """s6 写的文件末尾带换行。

    不剥掉的话 Authorization 头会变成 `Bearer <token>\\n`，直接把请求写坏。
    """
    (tmp_path / "TOKEN").write_text("abc123\n", encoding="utf-8")
    assert read_container_env("TOKEN", environ={}, s6_dir=tmp_path) == "abc123"


def test_returns_none_when_absent_everywhere(tmp_path: Path):
    assert read_container_env("TOKEN", environ={}, s6_dir=tmp_path) is None


def test_returns_none_when_s6_dir_missing(tmp_path: Path):
    """开发机上没有 s6 目录，不该因此炸掉。"""
    assert read_container_env("TOKEN", environ={}, s6_dir=tmp_path / "nope") is None


def test_empty_value_is_treated_as_absent(tmp_path: Path):
    """空 token 等同于没有，不该拿去发一个必然失败的请求。"""
    (tmp_path / "TOKEN").write_text("\n", encoding="utf-8")
    assert read_container_env("TOKEN", environ={}, s6_dir=tmp_path) is None
