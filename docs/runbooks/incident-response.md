# Incident Response Playbook

This document is a guide for handling critical incidents.

## On-Call Protocol

The on-call engineer is alerted via PagerDuty for any P1 or P2 incident.

## Incident Types & Responses

### P2: Payment Gateway Outage
-   **Detection:** Prometheus alert fires when the rate of 5xx errors from the payment endpoint exceeds 50%.
-   **Mitigation:**
    1.  The Payment Orchestrator will automatically attempt to failover to a secondary gateway.
    2.  If all gateways fail, disable checkout on the frontend with a maintenance message.
-   **Post-mortem:** Review gateway uptime SLAs and error budget.
