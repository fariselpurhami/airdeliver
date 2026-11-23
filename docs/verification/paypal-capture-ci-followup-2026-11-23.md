# CI failure follow-up and service-state evidence

Initial a121e9c run45104518676: RustFS job succeeded. Seaweed job passed804tests/1skip but failed later in the real learned-embedding seeder verification with Milvus get_flush_state gRPC UNAVAILABLE/socket closed. This does not prove an application regression, OOM or disk exhaustion. Failed-job rerun API was403, so no rerun happened.

Add diagnostic compose ps/all and container State/RestartCount inspection before existing disposable-stack logs/cleanup. Does not suppress failure or retry the seeder, relax assertions, alter containers, or change application runtime. This commit starts a fresh full CI check, whose success is still required before merge.
