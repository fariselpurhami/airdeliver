# Redis cold-burst admission

This replaces the unmerged eight-connection experiment, not a claim of arbitrary scale.

One native async connection and one admission slot bound connection handshakes. No Redis command retries, because an uncertain INCR must not be replayed. Read budget0.5seconds and total admission budget1second, including queue. Outage still returns503 without granting admission and cancellation propagates.

Full-suite cold stress previously reproduced99success/50quota/1storage503 with0.25second socket budget, including with a single connection and protocol2. Actual read timeout was observed. With the new bounded budget two consecutive full runs passed1246tests5skipped, each containing five150request cold bursts,100admitted+50quota and zero storage503. First measured burst0.37..0.40seconds, subsequent0.02..0.03. This supports a cold-start scheduling/read-budget explanation but does not isolate scheduler vs server latency as root cause. Explicit total-burst bound and original event-loop heartbeat test retained. Broader remote/network/production load remains unmeasured. No assertion weakened.
