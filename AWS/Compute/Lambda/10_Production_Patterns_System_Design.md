# AWS Lambda — Production Patterns & System Design

## Pattern 1: Fan-Out / Fan-In

```mermaid
flowchart TD
    TRIGGER["S3 Upload / API Request"] --> SNS["SNS Topic"]
    SNS --> LA["Lambda A\n(process shard 1)"]
    SNS --> LB["Lambda B\n(process shard 2)"]
    SNS --> LC["Lambda C\n(process shard 3)"]
    LA --> DDB["DynamoDB\n(aggregate results)"]
    LB --> DDB
    LC --> DDB

    style SNS fill:#6a0572,color:#fff
    style DDB fill:#264653,color:#fff
```

**Use when:** Processing large datasets in parallel. SNS for fan-out, DynamoDB/S3 for aggregation. Step Functions `Map` state is the managed alternative.

---

## Pattern 2: Saga (Distributed Transactions)

```mermaid
flowchart TD
    SF["Step Functions"] --> RESERVE["Reserve Inventory"]
    RESERVE -->|"Success"| CHARGE["Charge Payment"]
    CHARGE -->|"Success"| SHIP["Ship Order"]
    SHIP -->|"Success"| DONE["✅ Complete"]

    SHIP -->|"Fail"| COMP3["Undo Reserve\n+ Refund Payment"]
    CHARGE -->|"Fail"| COMP2["Undo Reserve"]
    RESERVE -->|"Fail"| COMP1["Nothing to undo"]

    style SF fill:#ff9f1c,color:#000
    style DONE fill:#2d6a4f,color:#fff
    style COMP1 fill:#d00000,color:#fff
    style COMP2 fill:#d00000,color:#fff
    style COMP3 fill:#d00000,color:#fff
```

Each step has a **compensating transaction.** If step N fails, run compensations for N-1 → 1 in reverse. Step Functions `Catch` blocks orchestrate this naturally.

---

## Pattern 3: Strangler Fig (Migration)

```mermaid
flowchart LR
    APIGW["API Gateway"] -->|"/v1/users"| MONO["Old Monolith\n(EC2)"]
    APIGW -->|"/v1/orders"| L1["Lambda\n(new microservice)"]
    APIGW -->|"/v1/payments"| L2["Lambda\n(new microservice)"]

    NOTE["Route by route,\nmonolith shrinks.\nLambda 'strangles'\nthe old system."]

    style MONO fill:#d00000,color:#fff
    style L1 fill:#2d6a4f,color:#fff
    style L2 fill:#2d6a4f,color:#fff
    style NOTE fill:#fff3cd,color:#000
```

---

## Pattern 4: Circuit Breaker

```mermaid
stateDiagram-v2
    [*] --> CLOSED
    CLOSED --> OPEN: Failures > threshold
    OPEN --> HALF_OPEN: After cooldown period
    HALF_OPEN --> CLOSED: Probe request succeeds
    HALF_OPEN --> OPEN: Probe request fails

    note right of CLOSED: Normal operation.\nAll requests forwarded.
    note right of OPEN: Return cached/default.\nDon't call failing service.
    note right of HALF_OPEN: Try one request.\nDecide based on result.
```

Store circuit state in **DynamoDB or ElastiCache.** Lambda Powertools has built-in circuit breaker for Python.

---

## Pattern 5: Event-Driven Pipeline

```mermaid
flowchart LR
    S3["S3 Upload"] --> L1["Lambda\n(validate)"]
    L1 --> SQS["SQS"]
    SQS --> L2["Lambda\n(process)"]
    L2 --> DDB["DynamoDB\n(store)"]
    L2 --> SNS["SNS\n(notify)"]

    style S3 fill:#2a9d8f,color:#fff
    style SQS fill:#264653,color:#fff
    style DDB fill:#1a535c,color:#fff
    style SNS fill:#6a0572,color:#fff
```

Each Lambda does **ONE thing.** Services between them handle buffering, retries, and decoupling.

---

## Pattern 6: API Gateway WebSocket + Lambda

```mermaid
sequenceDiagram
    participant User
    participant APIGW as API Gateway (WebSocket)
    participant Lambda
    participant DDB as DynamoDB

    User->>APIGW: WebSocket connect
    APIGW->>Lambda: $connect route
    Lambda->>DDB: Store connectionId
    
    User->>APIGW: Send message
    APIGW->>Lambda: $message route
    Lambda->>DDB: Look up recipient connectionIds
    Lambda->>APIGW: post_to_connection() for each recipient
    APIGW->>User: Deliver message

    User->>APIGW: Disconnect
    APIGW->>Lambda: $disconnect route
    Lambda->>DDB: Remove connectionId
```

> **[SDE2 TRAP]** API Gateway manages the persistent WebSocket connection (up to 2 hours). Lambda handles **discrete events** ($connect, $message, $disconnect) as short invocations. Lambda does NOT hold the connection.

**Limits:** Connection state in DynamoDB. Broadcasting to 10K connections = 10K `post_to_connection` calls. At extreme fan-out, consider ECS/EC2.

---

## When NOT to Use Lambda

| Scenario | Why Not | Use Instead |
|----------|---------|-------------|
| **> 15 min tasks** | Hard timeout limit | Fargate, ECS, EC2 |
| **Sustained high-throughput** (millions RPS constant) | Cost exceeds containers | ECS/EKS on Fargate |
| **Persistent connections** | Lambda is request-response | API GW WebSocket (limited), ECS |
| **Heavy GPU workload** | No GPU support | SageMaker, EC2 GPU |
| **Sub-10ms latency guarantee** | Cold starts make impossible | Containers with warm pools |
| **Large stateful processing** | 10GB /tmp + memory limits | EC2, EMR, Glue |
| **Binary protocols** | Lambda is HTTP/event-based | EC2, ECS |

---

## End-to-End Architecture — Paper Extraction System

```mermaid
flowchart TD
    USER["User"] -->|"POST /papers"| APIGW["API Gateway"]
    APIGW --> L_ACCEPT["Lambda: Accept Request\n(returns 202 + job ID)"]
    L_ACCEPT --> SQS["SQS Queue"]
    SQS --> SF["Step Functions"]
    
    subgraph PIPELINE["Step Functions Workflow"]
        VALIDATE["Validate\n(Lambda)"]
        DOWNLOAD["Download PDF\n(Lambda)"]
        EXTRACT["Extract Data\n(Lambda)"]
        STORE["Store to DB\n(SDK Integration)"]
        
        VALIDATE --> DOWNLOAD --> EXTRACT --> STORE
        
        DOWNLOAD -->|"Catch"| ERR["Error Handler\n(Lambda → DLQ + SNS alert)"]
        EXTRACT -->|"Catch"| ERR
    end
    
    SF --> PIPELINE

    style APIGW fill:#ff9f1c,color:#000
    style SF fill:#6a0572,color:#fff
    style PIPELINE fill:#1a535c,color:#fff
    style ERR fill:#d00000,color:#fff
```

**Why this architecture:**
- **API GW + accepting Lambda** → returns 202 immediately, no timeout issues
- **SQS** → buffers requests, handles backpressure
- **Step Functions** → per-step retry, visual debugging, saga rollback
- **SDK Integration** for DB store → skips Lambda, saves cost
- **Map state** for batch: process 1000 papers in parallel with `MaxConcurrency`

---

## Lambda vs Containers — Decision Framework

```mermaid
flowchart TD
    START{"Workload\nCharacteristics?"}
    START -->|"Spiky, unpredictable\n< 15 min per task"| LAMBDA["✅ Lambda"]
    START -->|"Sustained, predictable\n24/7 load"| FARGATE["✅ Fargate/ECS"]
    START -->|"GPU, long-running\nstateful processing"| EC2["✅ EC2"]

    LAMBDA -->|"Growing to\nsustained load?"| REVIEW{"Review\ncost monthly"}
    REVIEW -->|"> $500/mo"| FARGATE

    style LAMBDA fill:#2d6a4f,color:#fff
    style FARGATE fill:#264653,color:#fff
    style EC2 fill:#e76f51,color:#fff
```

### Cost Comparison at Scale (50 req/s, 24/7, 2GB, 3s avg)

| Platform | Monthly Cost | Ratio |
|----------|-------------|-------|
| **Lambda** | ~$12,986 | 43× |
| **Fargate** (10 tasks) | ~$711 | 2.4× |
| **EC2 Reserved** (3× c6g.xlarge) | ~$300 | 1× |

> Lambda wins for spiky, unpredictable, low-to-moderate volume. Containers/EC2 win for sustained, predictable, high-throughput.

---

## ⚠️ Gotchas & Edge Cases

1. **"Serverless" ≠ "zero ops."** You still own: IAM policies, concurrency limits, DLQ monitoring, cost alerts, log retention, deployment pipelines, incident response.
2. **Step Functions + Lambda + DynamoDB** is the canonical serverless stack. Know it cold for system design interviews.
3. **Fan-out without guardrails** overwhelms downstream services. Always set concurrency limits on both Lambda and Step Functions Map states.
4. **WebSocket API connection limit: 500 new connections/second.** For massive real-time apps, evaluate AppSync or dedicated WebSocket infrastructure.
5. **Cost modeling is non-negotiable.** Never assume Lambda is cheaper. Always run the numbers for your specific workload profile.

---

## 📌 Interview Cheat Sheet

**Patterns:** Fan-out (SNS/Map), Saga (Step Functions + compensations), Strangler Fig (API GW routing), Circuit Breaker (DDB state), Event Pipeline (SQS between single-purpose Lambdas)

**WebSocket:** API GW manages connection, Lambda handles discrete events. Lambda does NOT hold the connection. Store connectionIds in DynamoDB.

**When NOT Lambda:** >15min, sustained high throughput, GPU, persistent connections, sub-10ms latency, large stateful processing.

**Cost crossover:** Spiky/low volume → Lambda. Sustained/high volume → Fargate (18× cheaper). Predictable 24/7 → EC2 RI (43× cheaper).

**System design template:** API GW → Lambda (accept, 202) → SQS (buffer) → Step Functions → single-purpose Lambdas with per-step retry + error handling.

**The golden rule:** Model the cost. Always.
