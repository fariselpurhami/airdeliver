# Script ownership stage

Nine automation scripts move to dev, ops and ci. Relative aliases retain every
historical scripts/<name> command. Six implementations remain byte-identical.
Three root-sensitive scripts change only project-root resolution or the config
helper path. Standalone copied configure-dev-env fixtures remain supported.

Eight new tests cover aliases, imports, both CLI help forms and both backup path
forms against a fake Docker executable. No database is contacted by these local
checks. Twenty-six combined script/doc/entrypoint tests pass. Real disposable
Docker Compose setup and backup/restore tests remain full CI requirements.
No download helper, catalog synthesis, owner backup or owner stack runs here.
No deployment, owner migration, provider/payment calls or spend.
