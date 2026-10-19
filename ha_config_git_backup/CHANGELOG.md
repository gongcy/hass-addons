# Changelog

## 2.1.0

### Changed

- Files that match an exclude pattern are now removed from the repository on
  the next run. Previously they stayed in the working copy with their last
  content, so adding a pattern for a file that was already backed up only
  froze it.
- Logs, commit messages and git commit dates use Home Assistant's time zone
  instead of UTC.

## 2.0.0

First public release.

### Breaking

- `repo_url` no longer has a default value and must be configured. Previous
  builds shipped with a hard-coded repository address.
- `commit_author_email` default changed to `ha-config-backup@local`.

### Added

- HTTPS authentication with a personal access token, alongside SSH keys.
  The protocol is chosen automatically from `repo_url`.
- `exclude` option for additional rsync patterns, appended to the built-in
  defaults.
- `host_key` option to pin an SSH host key explicitly.
- Option labels and descriptions in English and Simplified Chinese.

### Changed

- Host key handling is now trust-on-first-use by default instead of a
  hard-coded key. Host key checking is never disabled.
- `.storage/core.restore_state` and
  `.storage/bluetooth.passive_update_processor` are excluded — pure runtime
  state rewritten every few minutes.
- scp-style URLs (`git@host:path`) are rejected with guidance, because they
  silently drop the port.
