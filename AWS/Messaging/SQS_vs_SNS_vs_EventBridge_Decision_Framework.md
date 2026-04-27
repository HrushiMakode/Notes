# SQS vs SNS vs EventBridge — Decision Framework & Architecture Patterns

## The Decision Matrix

| Scenario | Use This | Why |
|----------|----------|-----|
| 1 producer, 1 consumer, task processing | **SQS** | Simple queue, durable |
| 1 producer, N consumers, all need every msg | **SNS → SQS** | Fan-out + durability |
| Strict ordering per entity | **SQS FIFO** | MessageGroupId per entity |
| Ordered fan-out | **SNS FIFO → SQS FIFO** | Ordered broadcast |
| Complex routing, growing ecosystem | **EventBridge** | Content-based routing, schema registry |
| React to AWS service events | **EventBridge** | AWS emits to default bus natively |
| Scheduled / delayed one-time actions | **EventBridge Scheduler** | Per-item at scale |
| Ultra-high throughput (>10K/sec) | **SQS or Kinesis** | EventBridge has 10K/sec limit |
| Need replay / event history | **EventBridge** (archive) | Unique feature |
| Cross-account event routing | **EventBridge** | Native bus-to-bus |
| Email / SMS notifications | **SNS** | Direct protocol support |
| Buffer fast producer ↔ slow consumer | **SQS** | That's what queues do |

---

## The Quick Decision Flow

```mermaid
flowchart TD
    START{"How many consumers\nneed this message?"} -->|"ONE"| SQS_Q{"Need strict ordering?"}
    SQS_Q -->|"No"| STD["SQS Standard"]
    SQS_Q -->|"Yes"| FIFO["SQS FIFO\nMessageGroupId = entityId"]

    START -->|"MULTIPLE"| MULTI{"Routing complexity?"}
    MULTI -->|"Simple type-based\nfan-out"| SNS_SQS["SNS → SQS Fan-Out"]
    MULTI -->|"Complex nested\nrule-based"| EB["EventBridge"]

    MULTI -->|"AWS service events?"| EB
    MULTI -->|"Need replay /\nschema / cross-acct?"| EB
    MULTI -->|">10K events/sec?"| SNS_SQS

    style STD fill:#2d6a4f,color:#fff
    style FIFO fill:#1a535c,color:#fff
    style SNS_SQS fill:#ff9f1c,color:#000
    style EB fill:#6a0572,color:#fff
```

## They're Complementary, Not Competing

```mermaid
flowchart LR
    subgraph Layer1["Smart Routing"]
        AWS_EVT["AWS Service Events"] --> EB_DEF["EventBridge\nDefault Bus"]
        APP_EVT["App Events"] --> EB_CUST["EventBridge\nCustom Bus"]
    end

    subgraph Layer2["Fan-Out"]
        EB_DEF -->|"rule"| SNS1["SNS Topic"]
        EB_CUST -->|"rule"| SNS2["SNS Topic"]
    end

    subgraph Layer3["Durability + Throttling"]
        SNS1 --> SQS1["SQS"]
        SNS1 --> SQS2["SQS"]
        SNS2 --> SQS3["SQS"]
    end

    subgraph Layer4["Processing"]
        SQS1 --> L1["Lambda A"]
        SQS2 --> L2["Lambda B"]
        SQS3 --> L3["Lambda C"]
    end

    style EB_DEF fill:#6a0572,color:#fff
    style EB_CUST fill:#6a0572,color:#fff
    style SNS1 fill:#ff9f1c,color:#000
    style SNS2 fill:#ff9f1c,color:#000
    style SQS1 fill:#1a535c,color:#fff
    style SQS2 fill:#1a535c,color:#fff
    style SQS3 fill:#1a535c,color:#fff
```

**Magic phrase:** "EventBridge for routing, SNS for fan-out, SQS for durability and throttling."

---

## Architecture Patterns

### Pattern 1: Choreography Saga (Event-Driven)

```mermaid
flowchart LR
    OS["Order Service"] -->|"OrderCreated"| EB["EventBridge"]
    EB -->|"rule"| PS["Payment Service"]
    PS -->|"PaymentSucceeded"| EB
    PS -->|"PaymentFailed"| EB
    EB -->|"rule: PaymentSucceeded"| IS["Inventory Service"]
    EB -->|"rule: PaymentFailed"| OS
    IS -->|"InventoryReserved"| EB
    IS -->|"InventoryFailed"| EB
    EB -->|"rule: InventoryReserved"| SS["Shipping Service"]
    EB -->|"rule: InventoryFailed"| PS
    EB -->|"rule: any event"| AUDIT["Audit Service"]

    style EB fill:#ff9f1c,color:#000
    style AUDIT fill:#6c757d,color:#fff
```

- Each service emits events, others react
- Pro: fully decoupled. Con: hard to debug (no single view of state)
- **Better approach:** Step Functions for critical path + EventBridge for side effects

### Pattern 2: SNS+SQS Fan-Out (The Classic)
```
Service → SNS Topic → SQS Queue A → Lambda A (with DLQ, maxConcurrency)
                    → SQS Queue B → Lambda B (independent retry)
                    → SQS Queue C → Lambda C (independent scaling)
```
- Each consumer is isolated: own DLQ, own retry, own scaling

### Pattern 3: Load Leveling (Backpressure)
```
100K spike → SQS (absorbs all instantly) → Lambda (maxConcurrency: 50) → DB (safe at 50 TPS)
```
- Queue drains over time. Zero messages dropped.

### Pattern 4: Idempotency at Scale

```mermaid
flowchart TD
    MSG["Consumer receives message"] --> CHECK{"Check idempotency store:\nseen this event ID?"}
    CHECK -->|"YES\nalready processed"| SKIP["Skip processing\nDelete message"]
    CHECK -->|"NO\nfirst time"| PROCESS["Process the message"]
    PROCESS --> WRITE["Write result + eventId\nto idempotency store"]
    WRITE --> DELETE["Delete message from queue"]

    style SKIP fill:#6c757d,color:#fff
    style DELETE fill:#2d6a4f,color:#fff
```

- **Idempotency key:** use original event ID from body, NOT SQS MessageId
- AWS Powertools has `@idempotent` decorator built-in

---

## Every Design Must Address These 5 Things

1. **Idempotency** — "consumers use DynamoDB-based dedup"
2. **Dead Letter Queues** — "failed msgs go to DLQ, alert on depth > 0"
3. **Backpressure** — "maxConcurrency protects downstream"
4. **Monitoring** — "queue depth, message age, DLQ depth, consumer errors"
5. **Retry strategy** — "exponential backoff, maxReceiveCount before DLQ"

---

## Senior-Level Gotchas

1. Event ordering across services is an illusion — each service processes at its own speed
2. Exactly-once is a system property, not a service feature — needs idempotent consumers + dedup
3. Don't over-event — internal function calls don't need a queue
4. Schema evolution — additive-only changes (add fields, never remove/rename)
5. Testing event-driven systems — invest in correlation IDs, structured logging, archive+replay
