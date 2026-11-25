# API tool ownership

Nine original API-root maintenance implementations move into tools. Six remain
byte-identical. The seeder pins its API import root for existing direct CLI use
from arbitrary working directories. Two retain their exact historical file-relative target meaning
using an adjusted parent depth. Original filenames stay explicit import/CLI
compatibility entrypoints; canonical CLI uses python -m tools.<module>.

Dangerous helpers are not imported or run by layout validation. Nineteen wrapper,
hash and identity contracts use mocked dispatch, except the already import-safe
seeder identity. Existing seeder/Milvus contracts remain. Focused result:
44 passed, 4 skipped. Real full storage-backed CI is required before merge.

The original create_db_and_tables model-discovery parent expression is suspicious
and deliberately not repaired in this move. Operational review remains required.
No owner stack, database reset, model download, migration, provider/payment call,
deployment or spend is performed.
