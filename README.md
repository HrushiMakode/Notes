# 📒 Notes

A collection of in-depth technical notes, learnings, and revision guides — built for SDE2/SDE3 interview preparation and beyond.

---

## ☁️ AWS

### Storage

| Topic | Description |
|-------|-------------|
| [S3 — Interview Revision Notes](./AWS/S3/S3_revision.md) | Object vs Block vs File storage, S3 data model, consistency model, storage classes & lifecycle policies, versioning & MFA Delete, 4-layer access control (IAM / Bucket Policy / ACL / Block Public Access), pre-signed URLs, encryption (SSE-S3/KMS/C, CSE, envelope encryption), performance internals (partitioning, multipart uploads, byte-range fetches, Transfer Acceleration), event notifications & EventBridge integration, replication (CRR/SRR), and static website hosting. |

### Networking

| Topic | Description |
|-------|-------------|
| [VPC — Interview Revision Notes](./AWS/VPC/VPC_revision.md) | Networking fundamentals (OSI layers, CIDR), VPC architecture, subnets (public vs private), route tables & longest-prefix match, Internet Gateway, NAT Gateway, Security Groups vs NACLs, VPC Peering, VPC Endpoints (Gateway & Interface), Transit Gateway, DNS in VPC, Flow Logs, and production design patterns (3-tier VPC, egress VPC, shared services). |

### Messaging & Event-Driven Architecture

| Topic | Description |
|-------|-------------|
| [SQS — Interview Revision Notes](./AWS/Messaging/SQS/SQS_revision.md) | Message lifecycle, Standard vs FIFO queues, MessageGroupId, Dead Letter Queues (DLQ), Lambda + SQS integration (partial batch failures, scaling, maxConcurrency), cost optimization, monitoring metrics, and common patterns (claim-check, load leveling, backpressure). |
| [SNS — Interview Revision Notes](./AWS/Messaging/SNS/SNS_revision.md) | Pub/sub model, subscription protocols, message filtering (attribute & payload-based), FIFO topics, SNS + SQS fan-out pattern, delivery retries & DLQ (SNS DLQ vs SQS DLQ), and raw message delivery. |
| [EventBridge — Interview Revision Notes](./AWS/Messaging/EventBridge/EventBridge_revision.md) | Serverless event bus, event structure, content-based rule routing, input transformers, Archive & Replay, Schema Registry, EventBridge Scheduler (one-time & recurring), Pipes, cross-account/cross-region routing, retry handling, and cost model. |
| [SQS vs SNS vs EventBridge — Decision Framework](./AWS/Messaging/SQS_vs_SNS_vs_EventBridge_Decision_Framework.md) | When to use which service, decision flow chart, complementary layering pattern (EventBridge → SNS → SQS), architecture patterns (choreography saga, fan-out, load leveling, idempotency), and the 5 things every messaging design must address. |

---

> *More sections (Python, DSA, System Design, Projects) coming soon.*
