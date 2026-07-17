# deploy/ — export auto-delivery

Ship chat-export zips from a rig to the knight and auto-ingest them, using the
existing key-based ssh alias. Two halves:

- `push-exports.ps1` — runs on the **rig**: uploads `data-*.zip` / `takeout-*.zip`
  from Downloads to the knight drop zone (atomically), then touches a trigger.
- `chronicler-ingest.{path,service}` — run on the **knight**: a systemd path unit
  watches for the trigger and runs `run.py ingest`.

## Rig side (Windows)

Run after a download (or wire it to a scheduled task / folder watcher later):

```powershell
powershell -File deploy\push-exports.ps1
```

Defaults: source `~\Downloads`, remote alias `l5gn-castle`, drop zone
`vault/chat_threads/zip_downloads`. Override with `-Source` / `-Remote` /
`-DropZone`. Sent zips move to `~\Downloads\_pushed\`.

## Knight side (Ubuntu, user services)

Install the watcher once (assumes the toolkit at `~/L5GN-Tools`, the venv at
`~/L5GN-Tools/.venv`, and `chronicler_home` = `~/vault`):

```bash
mkdir -p ~/.config/systemd/user
cp ~/L5GN-Tools/deploy/chronicler-ingest.service ~/.config/systemd/user/
cp ~/L5GN-Tools/deploy/chronicler-ingest.path    ~/.config/systemd/user/
sudo loginctl enable-linger "$USER"          # let user services run headless (no login)
systemctl --user daemon-reload
systemctl --user enable --now chronicler-ingest.path
```

Verify / observe:

```bash
systemctl --user status chronicler-ingest.path
journalctl --user -u chronicler-ingest.service -f     # service runs
tail -f ~/vault/ingest.log                            # ingest output
```

## Flow

1. Rig: `push-exports.ps1` uploads zips, then touches `…/zip_downloads/.ingest-request`.
2. Knight: the `.path` unit sees the trigger → starts `.service`.
3. `.service` deletes the trigger (re-arming the watcher) and runs `run.py ingest`
   with the venv Python → intake unpacks the zips → pipeline updates `chronicler.db`.
4. `run.py consume` (or its own schedule) then reads the refreshed vault.

Notes: the trigger-file design means the watcher never fires on a half-transferred
zip. `run.py deposit`/`consume`/`verify` stay stdlib-only; only ingest needs the venv.
