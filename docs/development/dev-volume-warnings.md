# Dev volume warnings without deleting data

Run from the repository root. These helpers never remove volumes or change their labels.

## Read-only inventory

```bash
python3 scripts/inspect_dev_volumes.py
```

It prints resolved Compose volume names/mounts, all matching project volumes, references from running and stopped containers, and Docker's size/refcount table. It does not print resolved service environments. Keep the output private because infrastructure names are included. Size reporting can be slow or unavailable with some volume drivers; missing size is not zero. No reference does not prove data is unwanted or authorize deletion.

## Correct the cause, not only the output

Compose reports old project-labelled volumes whose physical names no longer
match the current declared volume name. Its reconciler deliberately leaves
these data-bearing orphans untouched. Source:
https://github.com/docker/compose/blob/v5.8.0/pkg/compose/reconcile.go

The inventory classifies current-config volumes and volumes referenced by any
running or stopped container as protected. An unreferenced stale volume is only
a review candidate, never disposable by default.

Before any owner-machine mutation:
1. Capture the inventory and the current resolved mount list.
2. Identify each old volume's data and retention need with the owner.
3. If retention is needed, choose a driver-supported export and restore route.
   Prove the restored archive before removing the original; live databases need
   application-consistent backups. Check free disk before copying.
4. Present the exact old-volume list, archive/backup destination, downtime and
   rollback route for explicit approval. Recheck all container references just
   before any approved removal.
5. Leave active volume names and service mounts unchanged. Verify ordinary
   Compose no longer reports the exact stale-label warning afterward.

Do not repoint services to old data, alter Compose project identity, or mark
volumes external merely to make output quiet. No prune or down-v. Docker local
volumes do not provide an in-place rename/relabel operation, so archiving under
a new name or removing the old volume is a real data operation, not metadata
housekeeping.

## Optional warning filter, not a repair

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


## Owner execution receipt, November25,2026

At18:23 Cairo, the owner supplied output of the separately approved guarded removal command. It listed the seven stale volumes and verified all seven absent. The command used no force, prune, down or other volume removal. This is owner-supplied execution evidence, not a Docker session operated by this repository change. The other five historical volumes and current mounts were outside the approved removal scope. Size was not established and no archive was requested. At18:25 Cairo, the owner supplied ordinary combined Compose ps output: api, api-worker and web were all healthy and no stale-label warning appeared. This confirms the owner-observed repair at that time, not an ongoing monitoring guarantee. Do not repeat deletion or treat this historical approval as authority for any future volume.
