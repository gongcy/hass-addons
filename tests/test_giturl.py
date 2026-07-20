import pytest

from hacgb.errors import InvalidRepoUrlError
from hacgb.giturl import GitUrl, Scheme, parse_git_url


def test_ssh_url_with_port():
    u = parse_git_url("ssh://git@git.example.com:2222/team/repo.git")
    assert u.scheme is Scheme.SSH
    assert u.host == "git.example.com"
    assert u.port == 2222


def test_ssh_url_without_port():
    u = parse_git_url("ssh://git@git.example.com/team/repo.git")
    assert u.scheme is Scheme.SSH
    assert u.host == "git.example.com"
    assert u.port is None


def test_https_url_with_port():
    u = parse_git_url("https://git.example.com:8443/team/repo.git")
    assert u.scheme is Scheme.HTTPS
    assert u.host == "git.example.com"
    assert u.port == 8443


def test_https_url_without_port():
    u = parse_git_url("https://github.com/user/repo.git")
    assert u.scheme is Scheme.HTTPS
    assert u.host == "github.com"
    assert u.port is None


def test_absolute_path_is_local():
    """本地 bare 仓库，端到端测试依赖它。"""
    u = parse_git_url("/srv/git/repo.git")
    assert u.scheme is Scheme.LOCAL
    assert u.host == ""
    assert u.port is None


def test_file_url_is_local():
    u = parse_git_url("file:///srv/git/repo.git")
    assert u.scheme is Scheme.LOCAL


def test_scp_syntax_is_rejected():
    """scp 短语法无法表达端口，会静默退回 22。直接拒绝。"""
    with pytest.raises(InvalidRepoUrlError):
        parse_git_url("git@github.com:user/repo.git")


def test_scp_rejection_message_shows_correct_form():
    """报错要告诉用户正确写法，不能只说'不支持'。"""
    with pytest.raises(InvalidRepoUrlError) as excinfo:
        parse_git_url("git@github.com:user/repo.git")
    assert "ssh://" in str(excinfo.value)


def test_empty_url_is_rejected():
    with pytest.raises(InvalidRepoUrlError):
        parse_git_url("")


def test_whitespace_only_url_is_rejected():
    with pytest.raises(InvalidRepoUrlError):
        parse_git_url("   ")


def test_url_is_stripped_before_parsing():
    """用户从网页复制常带首尾空白。"""
    u = parse_git_url("  https://github.com/user/repo.git  ")
    assert u.scheme is Scheme.HTTPS
    assert u.host == "github.com"


def test_http_is_treated_as_https_scheme_family():
    """明文 http 也走 token 认证路径。"""
    u = parse_git_url("http://git.example.com/user/repo.git")
    assert u.scheme is Scheme.HTTPS


def test_git_url_is_immutable():
    from dataclasses import FrozenInstanceError

    u = parse_git_url("https://github.com/user/repo.git")
    with pytest.raises(FrozenInstanceError):
        u.host = "evil.com"  # type: ignore[misc]
