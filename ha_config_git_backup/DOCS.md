# HA Config Git Backup

Periodically backs up your Home Assistant configuration directory to a Git
repository of your choice.

## Before you start

**The target repository must be private.** The backup includes `.storage`,
which holds long-lived access tokens that grant full control over your Home
Assistant instance. Never point this add-on at a public repository.

**One repository or branch per instance.** If two Home Assistant instances
push to the same repository and branch, each run overwrites the other's
backup completely — and because every push succeeds, nothing reports an
error.

## Setup

### SSH (recommended)

1. Create an empty private repository on your Git host.
2. Set `repo_url` to the full SSH URL, for example
   `ssh://git@github.com/youruser/ha-backup.git`. Note that scp-style URLs
   (`git@github.com:youruser/ha-backup.git`) are rejected — they cannot
   express a port.
3. Start the add-on. It generates an SSH key pair and prints the public key
   to the log.
4. Add that public key as a **deploy key with write access** on your
   repository.
5. Restart the add-on.

### HTTPS

1. Create an empty private repository.
2. Set `repo_url` to the HTTPS URL, e.g.
   `https://github.com/youruser/ha-backup.git`.
3. Create a personal access token with write access to that repository and
   put it in `token`.
4. Leave `username` at its default unless your host rejects it.

The token is passed to Git through `GIT_ASKPASS`; it is never written to
disk and never stored in `.git/config`.

## What gets backed up

Everything under the configuration directory except:

- `home-assistant_v2.db` and its WAL/SHM sidecars
- Logs and crash dumps
- `.cloud/` (Nabu Casa credentials)
- `tts/`, `deps/`, `.cache/`, `__pycache__/`
- `.storage/core.restore_state` and
  `.storage/bluetooth.passive_update_processor` — pure runtime state,
  rewritten every few minutes, of no value for recovery

`secrets.yaml` and the rest of `.storage` **are** included: the registries in
`.storage` are what a real recovery depends on.

Add your own patterns through the `exclude` option. They are appended to the
built-in list, which always applies. The working copy's own `.git/` directory
is always excluded and cannot be overridden.

Excluding a file that is already in the repository removes it on the next run
(the deletion is committed). Its earlier versions stay in the git history, so
rewrite the history yourself if the file held secrets.

Timestamps in logs, commit messages and git commit dates use Home Assistant's
time zone.

## Expect a commit almost every run

The registries under `.storage` are rewritten frequently by Home Assistant,
so the "no changes, skipping" path rarely triggers. This is inherent to
backing up `.storage`, not a fault.

## Restoring

This add-on does not restore. Recovery is infrequent and needs human
judgement, so do it by hand:

```bash
git clone <your repo url>
```

## Host key verification

By default the host key is learned on first connection and pinned from then
on — any later change is rejected. This is standard SSH trust-on-first-use.

To pin explicitly instead, run `ssh-keyscan -p PORT HOST` and paste the full
output line into `host_key`.

Host key checking is never disabled.

## Limitations

- 32-bit architectures (armv7, armhf, i386) are not supported.
- The database is not included, so history (recorder) is not backed up. Use
  Home Assistant's own full backup for that.
- The add-on runs inside Home Assistant, so it cannot back up while Home
  Assistant is down.
- Home Assistant writes to `.storage` continuously, so a run may capture a
  file mid-write. At daily frequency this is unlikely and the next run
  corrects it.
