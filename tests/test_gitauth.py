import subprocess
from pathlib import Path

from hacgb.gitauth import ASKPASS_PATH, build_auth_env
from hacgb.giturl import parse_git_url
from hacgb.sshkeys import SshKeys

REPO_ROOT = Path(__file__).resolve().parent.parent
ASKPASS_SCRIPT = REPO_ROOT / "ha_config_git_backup/rootfs/opt/hacgb/askpass.sh"


def _ssh_env(ssh_dir: Path, host_key: str = "") -> dict[str, str]:
    return build_auth_env(
        parse_git_url("ssh://git@git.example.com:2222/u/r.git"),
        SshKeys(ssh_dir), username="oauth2", token="", host_key=host_key,
    )


def _https_env(ssh_dir: Path, token: str = "tok-123") -> dict[str, str]:
    return build_auth_env(
        parse_git_url("https://github.com/u/r.git"),
        SshKeys(ssh_dir), username="oauth2", token=token, host_key="",
    )


def test_ssh_sets_git_ssh_command(ssh_dir: Path):
    env = _ssh_env(ssh_dir)
    assert "GIT_SSH_COMMAND" in env
    assert str(ssh_dir / "id_ed25519") in env["GIT_SSH_COMMAND"]


def test_ssh_uses_tofu_without_host_key(ssh_dir: Path):
    env = _ssh_env(ssh_dir)
    assert "StrictHostKeyChecking=accept-new" in env["GIT_SSH_COMMAND"]


def test_ssh_uses_strict_with_host_key(ssh_dir: Path):
    env = _ssh_env(ssh_dir, host_key="[git.example.com]:2222 ssh-ed25519 AAAA")
    assert "StrictHostKeyChecking=yes" in env["GIT_SSH_COMMAND"]


def test_ssh_does_not_set_askpass(ssh_dir: Path):
    env = _ssh_env(ssh_dir)
    assert "GIT_ASKPASS" not in env


def test_https_sets_askpass_triplet(ssh_dir: Path):
    env = _https_env(ssh_dir)
    assert env["GIT_ASKPASS"] == ASKPASS_PATH
    assert env["HACGB_GIT_USERNAME"] == "oauth2"
    assert env["HACGB_GIT_PASSWORD"] == "tok-123"


def test_https_does_not_set_ssh_command(ssh_dir: Path):
    env = _https_env(ssh_dir)
    assert "GIT_SSH_COMMAND" not in env


def test_token_never_appears_in_any_git_config_variable(ssh_dir: Path):
    """token 只能经 askpass 传递。

    一旦它出现在 GIT_CONFIG_* 或类似变量里，就可能被写进 .git/config
    或出现在 git 的报错输出中。
    """
    env = _https_env(ssh_dir, token="super-secret")
    leaked = [
        k for k, v in env.items()
        if "super-secret" in v and k != "HACGB_GIT_PASSWORD"
    ]
    assert leaked == []


def test_terminal_prompt_disabled_for_all_schemes(ssh_dir: Path):
    """容器里没人能回答交互提示，必须禁掉。"""
    assert _ssh_env(ssh_dir)["GIT_TERMINAL_PROMPT"] == "0"
    assert _https_env(ssh_dir)["GIT_TERMINAL_PROMPT"] == "0"


def test_local_scheme_needs_no_credentials(ssh_dir: Path):
    env = build_auth_env(
        parse_git_url("/srv/git/repo.git"),
        SshKeys(ssh_dir), username="oauth2", token="", host_key="",
    )
    assert "GIT_SSH_COMMAND" not in env
    assert "GIT_ASKPASS" not in env
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_askpass_script_returns_username_for_username_prompt():
    """直接调脚本验证它遵守 git 的 askpass 契约。"""
    result = subprocess.run(
        [str(ASKPASS_SCRIPT), "Username for 'https://github.com': "],
        capture_output=True, text=True,
        env={"HACGB_GIT_USERNAME": "alice", "HACGB_GIT_PASSWORD": "pw", "PATH": "/bin:/usr/bin"},
    )
    assert result.stdout.strip() == "alice"


def test_askpass_script_returns_password_for_password_prompt():
    result = subprocess.run(
        [str(ASKPASS_SCRIPT), "Password for 'https://alice@github.com': "],
        capture_output=True, text=True,
        env={"HACGB_GIT_USERNAME": "alice", "HACGB_GIT_PASSWORD": "pw", "PATH": "/bin:/usr/bin"},
    )
    assert result.stdout.strip() == "pw"


def test_askpass_script_defaults_to_password():
    """URL 里已带用户名时 git 只问密码，提示词形态可能不同。"""
    result = subprocess.run(
        [str(ASKPASS_SCRIPT), "some other prompt"],
        capture_output=True, text=True,
        env={"HACGB_GIT_USERNAME": "alice", "HACGB_GIT_PASSWORD": "pw", "PATH": "/bin:/usr/bin"},
    )
    assert result.stdout.strip() == "pw"


def test_askpass_script_is_executable():
    import os
    assert os.access(ASKPASS_SCRIPT, os.X_OK)
