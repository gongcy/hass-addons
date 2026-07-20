import stat
from pathlib import Path

from hacgb.sshkeys import SshKeys

EXAMPLE_HOST_KEY_LINE = (
    "[git.example.com]:2222 ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAIExampleKeyForTestingPurposesOnly000000000"
)


def test_first_call_generates_keypair(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    created = keys.ensure()
    assert created is True
    assert (ssh_dir / "id_ed25519").exists()
    assert (ssh_dir / "id_ed25519.pub").exists()


def test_second_call_does_not_regenerate(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    keys.ensure()
    before = (ssh_dir / "id_ed25519").read_bytes()
    created = keys.ensure()
    assert created is False
    assert (ssh_dir / "id_ed25519").read_bytes() == before


def test_private_key_is_owner_only(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    keys.ensure()
    mode = stat.S_IMODE((ssh_dir / "id_ed25519").stat().st_mode)
    assert mode == 0o600


def test_ssh_dir_is_owner_only(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    keys.ensure()
    assert stat.S_IMODE(ssh_dir.stat().st_mode) == 0o700


def test_generated_key_is_ed25519(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    keys.ensure()
    assert keys.public_key().startswith("ssh-ed25519 ")


def test_known_hosts_holds_provided_key(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    keys.write_known_hosts(EXAMPLE_HOST_KEY_LINE)
    assert EXAMPLE_HOST_KEY_LINE in (ssh_dir / "known_hosts").read_text(encoding="utf-8")


def test_known_hosts_is_empty_when_no_key_given(ssh_dir: Path):
    """没给 host_key 时文件要存在但为空，供 accept-new 写入。"""
    keys = SshKeys(ssh_dir)
    keys.write_known_hosts(None)
    assert (ssh_dir / "known_hosts").is_file()
    assert (ssh_dir / "known_hosts").read_text(encoding="utf-8").strip() == ""


def test_existing_known_hosts_is_preserved_without_key(ssh_dir: Path):
    """TOFU 记录下来的指纹不能被下次启动清掉，否则形同虚设。"""
    keys = SshKeys(ssh_dir)
    keys.write_known_hosts(None)
    (ssh_dir / "known_hosts").write_text("learned-by-tofu\n", encoding="utf-8")
    keys.write_known_hosts(None)
    assert "learned-by-tofu" in (ssh_dir / "known_hosts").read_text(encoding="utf-8")


def test_provided_key_overwrites_previous_content(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    keys.write_known_hosts(None)
    (ssh_dir / "known_hosts").write_text("stale\n", encoding="utf-8")
    keys.write_known_hosts(EXAMPLE_HOST_KEY_LINE)
    text = (ssh_dir / "known_hosts").read_text(encoding="utf-8")
    assert "stale" not in text
    assert EXAMPLE_HOST_KEY_LINE in text


def test_strict_mode_rejects_unknown_hosts(ssh_dir: Path):
    cmd = SshKeys(ssh_dir).git_ssh_command(strict=True)
    assert "StrictHostKeyChecking=yes" in cmd


def test_tofu_mode_accepts_new_hosts(ssh_dir: Path):
    cmd = SshKeys(ssh_dir).git_ssh_command(strict=False)
    assert "StrictHostKeyChecking=accept-new" in cmd


def test_never_disables_host_key_checking(ssh_dir: Path):
    """安全底线：任何模式下都不能退化成 no。"""
    keys = SshKeys(ssh_dir)
    assert "StrictHostKeyChecking=no" not in keys.git_ssh_command(strict=True)
    assert "StrictHostKeyChecking=no" not in keys.git_ssh_command(strict=False)


def test_git_ssh_command_pins_identity_and_known_hosts(ssh_dir: Path):
    cmd = SshKeys(ssh_dir).git_ssh_command(strict=False)
    assert "IdentitiesOnly=yes" in cmd
    assert "BatchMode=yes" in cmd
    assert str(ssh_dir / "id_ed25519") in cmd
    assert str(ssh_dir / "known_hosts") in cmd


def test_module_has_no_hardcoded_host():
    """通用化的核心目的：模块里不得再有任何具体主机。

    用通用模式检查而不是列举某个已知域名：列举本身就会把那个域名写进
    代码，而且只挡得住列举到的那一个。这里查的是任何域名字面量、IPv4
    字面量，以及被硬编码的 SSH 公钥。
    """
    import inspect
    import re

    from hacgb import sshkeys

    source = inspect.getsource(sshkeys)

    # 至少两级的点分名称才算主机名，借此把 id_ed25519.pub 这类文件名排除掉。
    hostname = re.compile(r"\b[\w-]+\.[\w-]+\.[a-z]{2,}\b|\b[\w-]+\.(?:com|net|org|top|io|cn|dev|me|xyz)\b")
    ipv4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")

    quoted = re.findall(r"""["']([^"']*)["']""", source)
    for literal in quoted:
        assert not hostname.search(literal), f"疑似硬编码主机名：{literal!r}"
        assert not ipv4.search(literal), f"疑似硬编码 IP：{literal!r}"
        assert "AAAA" not in literal, f"疑似硬编码公钥：{literal!r}"


def test_public_key_is_readable(ssh_dir: Path):
    keys = SshKeys(ssh_dir)
    keys.ensure()
    assert keys.public_key().startswith("ssh-ed25519 ")
