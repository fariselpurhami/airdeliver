# Dev volume warnings without deleting data

Run from the repository root. These helpers never remove volumes or change their labels.

## Read-only inventory

```bash
python3 scripts/inspect_dev_volumes.py
```

It prints resolved Compose volume names/mounts, all matching project volumes, references from running and stopped containers, and Docker's size/refcount table. It does not print resolved service environments. Keep the output private because infrastructure names are included. Size reporting can be slow or unavailable with some volume drivers; missing size is not zero. No reference does not prove data is unwanted or authorize deletion.

## Hide only the known mismatch warning

Use this wrapper instead of the same `docker compose` command. It supplies the existing combined dev files, `.env.dev` and project name. Pass the remaining Compose arguments unchanged:

```bash
python3 scripts/dev_compose_quiet_volumes.py ps
```

For an already-approved source-only refresh, use the same bounded service list and flags previously reviewed. The wrapper itself does not authorize a refresh:

```bash
python3 scripts/dev_compose_quiet_volumes.py up -d --no-deps --no-build --force-recreate api api-worker web
```

Only the exact known `airdeliver_dev_` volume-label mismatch warning is filtered. Other stderr, stdout and exit status pass through. This hides the warning, not the mismatch, and does not recover disk space. Direct Compose commands still display it. Use `--show-stale-volume-warnings` before the Compose arguments to show it again. A changed or unknown warning is deliberately not filtered.

Do not map old data volumes back into services solely to silence warnings. That can switch the database or search state. Declaring retained volumes external does not by itself remove mismatched Compose labels from other old volumes. Existing Docker volume labels cannot be changed with this helper.

## Deletion is separate and not authorized

No prune, `down -v`, removal list or backup claim is supplied here. Before proposing removal: inspect actual references (including stopped containers), identify the data and retention need, prepare an export route for that driver, verify the backup and restore process, and obtain explicit approval for the exact volume list. A live database needs an application-consistent backup, not a claim that copying changing files is sufficient. None of these owner-machine checks has been performed by this change.
