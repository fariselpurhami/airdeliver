# Disaster Recovery Plan

This document outlines the strategy for recovering the airdeliver platform in the event of a major failure.

## Objectives

-   **Recovery Time Objective (RTO):** 1 hour. The time it should take to restore service after an outage.
-   **Recovery Point Objective (RPO):** 15 minutes. The maximum acceptable amount of data loss.

## Procedures

1.  **Database Backup:**
    -   Automated point-in-time backups of the PostgreSQL database are taken every 5 minutes.
    -   Full daily snapshots are stored in a separate geographic region.
2.  **Infrastructure:**
    -   Our Kubernetes cluster is deployed across three availability zones (AZs).
    -   In the event of a full AZ failure, Kubernetes will automatically reschedule pods in healthy zones.
3.  **Failover Drill:**
    -   The engineering team will conduct a simulated failover drill every quarter to test this plan.
