# EC2 vs ECS vs Fargate vs Lambda — Decision Framework & Architecture Patterns

## The Compute Spectrum

```mermaid
flowchart LR
    BM["🔩 Bare Metal\n─────────\nYou own: EVERYTHING\nAWS owns: Power/Rack"] --> EC2_S["🖥️ EC2\n─────────\nYou own: OS + App\nAWS owns: HW + Hypervisor"]
    EC2_S --> ECS_S["📦 ECS on EC2\n─────────\nYou own: App + Docker\nAWS owns: HW + OS + Orch"]
    ECS_S --> FG_S["☁️ Fargate\n─────────\nYou own: Image only\nAWS owns: + Runtime"]
    FG_S --> LM_S["⚡ Lambda\n─────────\nYou own: Code only\nAWS owns: Everything"]

    style BM fill:#1b4332,color:#fff
    style EC2_S fill:#2d6a4f,color:#fff
    style ECS_S fill:#1a535c,color:#fff
    style FG_S fill:#6a0572,color:#fff
    style LM_S fill:#ff9f1c,color:#000
```

> ◄ **MORE CONTROL** ─────────────────── **MORE ABSTRACTION** ►

**Magic phrase:** "Match compute to workload — hybrid architectures win interviews."

---

## The Decision Matrix

| Scenario | Use This | Why |
|----------|----------|-----|
| Short event-driven task (<15 min) | **Lambda** | Pay per invocation, native triggers (S3, SQS, DynamoDB) |
| 24/7 API server, steady traffic | **ECS/Fargate** or **EC2** | Lambda per-ms billing too expensive at sustained RPS |
| Stateful process (in-memory cache, DB) | **EC2** | Persistent memory, local NVMe, full OS control |
| GPU workload (ML training/inference) | **EC2** (p/g family) | Fargate & Lambda have zero GPU support |
| Batch job, 5-60 min, fault-tolerant | **Fargate Spot** | Cheaper than Lambda, handles interruption via SQS redrive |
| Batch job, <15 min, embarrassingly parallel | **Lambda** | Massive parallelism, zero idle cost |
| Cron / Scheduled job, <15 min | **Lambda** + EventBridge rule | Simplest, zero infra |
| Cron / Scheduled job, >15 min | **Fargate** (ECS scheduled task) | No timeout limit |
| Microservices, small team (<10 devs) | **Fargate** | Zero infra management, per-task billing |
| Microservices, large fleet, steady load | **ECS on EC2** | Cost-optimized with RIs + bin-packing |
| Legacy monolith (8 GB+, slow boot) | **EC2** or **ECS on EC2** | Too heavy for Fargate/Lambda limits |
| Multi-cloud portability required | **EKS** (Kubernetes) | K8s is cloud-agnostic orchestration |
| Per-core licensed software (Oracle) | **EC2 Dedicated Host** | Socket/core placement control for licensing |
| HIPAA/PCI dedicated hardware | **EC2 Dedicated Instance** | Hardware isolation per-account |
| Real-time WebSocket / persistent conn | **ECS/Fargate** or **EC2** | Lambda max 15 min, no persistent connections |
| Ultra-low latency (<10ms p99) | **EC2** or **ECS on EC2** | No cold starts, kernel tuning possible |

---

## The Quick Decision Flow

```mermaid
flowchart TD
    START{"What does your\nworkload look like?"} -->|"Event-driven\n< 15 min"| LAMBDA["✅ Lambda"]
    START -->|"Long-running\nprocess"| LONG{"Need GPU or\nspecific OS kernel?"}
    START -->|"Stateful\n(DB, cache, broker)"| EC2_DIRECT["✅ EC2"]

    LONG -->|"Yes"| EC2_DIRECT
    LONG -->|"No"| TRAFFIC{"Traffic pattern?"}

    TRAFFIC -->|"Spiky /\nvariable"| FARGATE["✅ Fargate"]
    TRAFFIC -->|"Steady /\npredictable"| TEAM{"Team size &\nops maturity?"}

    TEAM -->|"Small team\nno dedicated DevOps"| FARGATE
    TEAM -->|"Large team\nSRE / platform eng"| ECS_EC2["✅ ECS on EC2\nwith RIs"]

    style LAMBDA fill:#ff9f1c,color:#000
    style FARGATE fill:#6a0572,color:#fff
    style ECS_EC2 fill:#1a535c,color:#fff
    style EC2_DIRECT fill:#2d6a4f,color:#fff
```

---

## The Five Decision Axes (Deep Dive)

### Axis 1 — Workload Profile

| Characteristic | Lambda | Fargate | ECS on EC2 | EC2 |
|---------------|--------|---------|-----------|-----|
| Max execution time | 15 min | Unlimited | Unlimited | Unlimited |
| Max memory | 10 GB | 120 GB | Instance-limited | Instance-limited |
| Max vCPU | 6 | 16 | Instance-limited | Instance-limited |
| GPU support | ❌ | ❌ | ✅ | ✅ |
| Persistent state | ❌ | ❌ (ephemeral disk) | ✅ (EBS) | ✅ (EBS + instance store) |
| Custom kernel / OS | ❌ | ❌ | ✅ | ✅ |
| Docker socket access | ❌ | ❌ | ✅ | ✅ |
| Windows support | ❌ | ⚠️ Limited | ✅ | ✅ |

> **[SDE2 TRAP]** Fargate ephemeral storage = 20 GB default (expandable to 200 GB), but it's wiped when the task stops. For persistent container storage, mount **EFS** — it's the only option on Fargate. On ECS/EC2, you can use EBS directly.

### Axis 2 — Operational Burden

```mermaid
flowchart LR
    subgraph ZERO["Zero Ops"]
        LAMBDA_OP["Lambda\n• No servers\n• No containers\n• No patching\n• No capacity planning"]
    end

    subgraph LOW["Low Ops"]
        FARGATE_OP["Fargate\n• Build Docker image\n• Define task CPU/mem\n• Configure service\n• No host management"]
    end

    subgraph MEDIUM["Medium Ops"]
        ECS_EC2_OP["ECS on EC2\n• Manage EC2 fleet\n• Patch OS / AMI\n• Capacity providers\n• Monitor host + container"]
    end

    subgraph HIGH["High Ops"]
        EC2_OP["Raw EC2 + ASG\n• Everything above\n• No orchestrator\n• Manual deploys\n• DIY service discovery"]
    end

    ZERO -.->|"increasing\ncontrol"| LOW -.-> MEDIUM -.-> HIGH

    style LAMBDA_OP fill:#ff9f1c,color:#000
    style FARGATE_OP fill:#6a0572,color:#fff
    style ECS_EC2_OP fill:#1a535c,color:#fff
    style EC2_OP fill:#2d6a4f,color:#fff
```

**The interview line:** *"We chose Fargate because our team is 6 engineers. Managing EC2 fleet patching, AMI pipelines, and capacity planning would consume ~30% of one engineer's time — more expensive than the Fargate pricing premium."*

### Axis 3 — Cost Structure

#### Traffic Pattern Determines Winner

```mermaid
flowchart LR
    subgraph SPIKY["Pattern A: Spiky / Event-driven"]
        direction TB
        S1["Traffic: ___/\___/\___"]
        S2["Winner: Lambda ✅"]
        S3["You pay: only during spikes"]
        S1 --- S2 --- S3
    end

    subgraph STEADY["Pattern B: Steady 24/7"]
        direction TB
        T1["Traffic: ════════════"]
        T2["Winner: EC2 + RI ✅"]
        T3["You pay: 72% less than on-demand"]
        T1 --- T2 --- T3
    end

    subgraph MIXED["Pattern C: Base + Peaks"]
        direction TB
        M1["Traffic: __/‾‾‾\__/‾‾‾\__"]
        M2["Winner: Hybrid ✅"]
        M3["Base=RI + Peaks=Spot/Fargate"]
        M1 --- M2 --- M3
    end

    style S2 fill:#ff9f1c,color:#000
    style T2 fill:#2d6a4f,color:#fff
    style M2 fill:#6a0572,color:#fff
```

#### Cost Comparison — 1000 RPS Sustained API (24/7)

| Compute | Config | Approx. Monthly Cost |
|---------|--------|---------------------|
| **Lambda** | 128 MB, 100ms avg, 1K RPS | ~$5,400 |
| **Fargate** | 0.5 vCPU + 1 GB × 4 tasks | ~$120 |
| **EC2 On-Demand** | m6i.large × 2 | ~$140 |
| **EC2 1-yr RI** | m6i.large × 2 | ~$85 |

> ⚠️ Lambda at sustained high RPS is **40-60× more expensive** than EC2/Fargate. But at 10 RPS avg with spikes to 200 RPS? Lambda wins massively because EC2 pays for idle.

#### Cost Crossover Points

| Transition | Approx. Crossover |
|-----------|-------------------|
| Lambda → Fargate is cheaper | ~**1M requests/day** (varies by memory + duration) |
| Fargate → ECS on EC2 is cheaper | Cluster utilization consistently **>70%** |
| On-Demand → Savings Plans worth it | Any workload running **>8 hours/day** |
| Spot worth the complexity | Fault-tolerant workloads with **>30% cost sensitivity** |

> **[SDE2 TRAP]** An interviewer asks: *"Which is cheaper, Lambda or Fargate?"* If you answer without asking about **traffic volume and pattern first**, you've already failed. The correct response is always: *"It depends — what's the request rate and traffic pattern?"*

### Axis 4 — Scaling Behavior

| Dimension | Lambda | Fargate | ECS on EC2 | EC2 ASG |
|-----------|--------|---------|-----------|---------|
| **Scale unit** | Single invocation | One task | One task (may need new instance) | One instance |
| **Scale speed** | Milliseconds | 30-60s | Seconds (capacity exists) → minutes (new instance) | 2-5 minutes |
| **Scale to zero** | ✅ Native | ✅ (desired=0) | ❌ Needs ≥1 instance | ❌ Slow restart from 0 |
| **Cold start** | 100ms-10s | 30-60s | Negligible (on existing host) | 2-5 min (full boot) |
| **Max concurrency** | 1000 default (increasable) | Account vCPU quota | Fleet size | Fleet size |
| **Granularity** | Per-request | 0.25 vCPU increments | Per-task | Per-instance |

```mermaid
flowchart LR
    subgraph RANGE1["0 — 100 RPS"]
        R1["⚡ Lambda\nZero idle cost\nPay per request"]
    end
    subgraph RANGE2["100 — 10K RPS"]
        R2["☁️ Fargate\nBalanced ops/cost\nPer-task billing"]
    end
    subgraph RANGE3["10K — 100K+ RPS"]
        R3["📦 ECS on EC2\nCost-optimized\nRI + bin-packing"]
    end

    RANGE1 --> RANGE2 --> RANGE3

    style R1 fill:#ff9f1c,color:#000
    style R2 fill:#6a0572,color:#fff
    style R3 fill:#1a535c,color:#fff
```

> **[SDE2 TRAP]** Lambda has a **per-region concurrency limit** (default 1000). If Service A eats 900 concurrency during a spike, Service B (in the same account/region) is starved to 100. Solution: **Reserved Concurrency** per function — you already covered this in your Lambda modules. Fargate doesn't have this shared-limit problem.

### Axis 5 — Hard Constraints (Eliminators)

These are non-negotiable. If any apply, options are immediately eliminated:

| Hard Constraint | ❌ Eliminated |
|----------------|--------------|
| Needs GPU | Lambda, Fargate |
| Execution > 15 minutes | Lambda |
| Specific OS kernel / kernel module | Lambda, Fargate |
| HIPAA/PCI dedicated hardware | Lambda, Fargate → EC2 Dedicated |
| Must scale to zero (zero idle cost) | ECS on EC2 (practically) |
| Docker socket / privileged mode | Lambda, Fargate |
| Per-core software licensing | Lambda, Fargate → EC2 Dedicated Host |
| Windows containers | Lambda, Fargate (limited) |
| Sub-ms latency to VPC resources | Lambda (ENI attach adds latency on cold start) |

---

## Architecture Patterns

### Pattern 1: The Hybrid (The Answer Interviewers Want)

```mermaid
flowchart TD
    INTERNET["Internet"] --> ALB["ALB"]
    
    subgraph STEADY["Steady Services (Fargate / ECS-EC2)"]
        API["Product API\n(Fargate)"]
        AUTH["Auth Service\n(Fargate)"]
        USER["User Service\n(Fargate)"]
    end

    subgraph STATEFUL["Stateful (EC2)"]
        REDIS["Redis Cluster\n(r6i.xlarge)"]
        ES["Elasticsearch\n(i3.2xlarge)"]
        ML["ML Inference\n(p4d.24xlarge)"]
    end

    subgraph EVENTS["Event-Driven (Lambda)"]
        THUMB["Image Resize\n(S3 trigger)"]
        WEBHOOK["Webhooks\n(API GW trigger)"]
        NOTIF["Notifications\n(SQS trigger)"]
    end

    subgraph BATCH["Batch (Fargate Spot)"]
        ETL["Data Transform\n5-20 min jobs"]
        REPORT["Report Gen\n10-30 min jobs"]
    end

    ALB --> API
    ALB --> AUTH
    ALB --> USER
    API --> REDIS
    API --> ES
    API --> ML
    API -->|"events"| SQS["SQS"]
    SQS --> NOTIF
    SQS --> ETL

    style API fill:#6a0572,color:#fff
    style AUTH fill:#6a0572,color:#fff
    style USER fill:#6a0572,color:#fff
    style REDIS fill:#2d6a4f,color:#fff
    style ES fill:#2d6a4f,color:#fff
    style ML fill:#2d6a4f,color:#fff
    style THUMB fill:#ff9f1c,color:#000
    style WEBHOOK fill:#ff9f1c,color:#000
    style NOTIF fill:#ff9f1c,color:#000
    style ETL fill:#1a535c,color:#fff
    style REPORT fill:#1a535c,color:#fff
```

**Why this works:** Each workload is on its optimal compute type. Interviewers want to see you **justify each choice**, not put everything on one platform.

### Pattern 2: Image/Video Processing Pipeline

```mermaid
flowchart LR
    UPLOAD["User Upload"] --> S3["S3 Bucket"]
    S3 -->|"S3 Event"| L1["Lambda\n(validate + metadata)\n< 30s"]
    L1 -->|"valid"| SQS["SQS Queue"]
    SQS --> FG["Fargate Spot\n(heavy transform)\n5-15 min"]
    FG --> S3OUT["S3 (processed)"]
    S3OUT -->|"S3 Event"| L2["Lambda\n(update DB + notify)\n< 5s"]
    L2 --> DDB["DynamoDB"]

    style L1 fill:#ff9f1c,color:#000
    style L2 fill:#ff9f1c,color:#000
    style FG fill:#6a0572,color:#fff
    style SQS fill:#1a535c,color:#fff
```

- **Lambda** for short validation/notification (event-driven, <1 min)
- **Fargate Spot** for heavy transform (too long for Lambda, fault-tolerant via SQS redrive, 70% cheaper than on-demand)
- **SQS** between them for buffering and retry

### Pattern 3: Monolith → Microservices Migration Path

```mermaid
flowchart TD
    subgraph PHASE1["Phase 1: Lift & Shift"]
        MON1["Monolith on EC2\n(same code, just moved)"]
    end

    subgraph PHASE2["Phase 2: Containerize"]
        MON2["Monolith in Docker\non ECS/Fargate\n(same code, containerized)"]
    end

    subgraph PHASE3["Phase 3: Decompose"]
        SVC1["Service A\n(Fargate)"]
        SVC2["Service B\n(Fargate)"]
        SVC3["Monolith\n(shrinking)"]
    end

    subgraph PHASE4["Phase 4: Optimize"]
        SVC4["Service A (Fargate)"]
        SVC5["Service B (Lambda)"]
        SVC6["Service C (Fargate)"]
        SVC7["Cache (EC2-Redis)"]
    end

    PHASE1 -->|"weeks"| PHASE2 -->|"months"| PHASE3 -->|"quarters"| PHASE4

    style MON1 fill:#2d6a4f,color:#fff
    style MON2 fill:#1a535c,color:#fff
    style SVC1 fill:#6a0572,color:#fff
    style SVC2 fill:#6a0572,color:#fff
    style SVC3 fill:#1a535c,color:#fff
    style SVC4 fill:#6a0572,color:#fff
    style SVC5 fill:#ff9f1c,color:#000
    style SVC6 fill:#6a0572,color:#fff
    style SVC7 fill:#2d6a4f,color:#fff
```

> **[SDE2 TRAP]** If an interviewer says "migrate this monolith to Lambda," the correct answer is: *"I wouldn't go directly to Lambda. The realistic path is: EC2 → containerize → decompose into services → selectively move event-driven pieces to Lambda."* Jumping straight to serverless from a monolith = rewrite, not migration.

### Pattern 4: Cost-Optimized Steady Fleet

```mermaid
flowchart TD
    subgraph FLEET["Compute Fleet — Cost Layers"]
        direction TB
        RI["Savings Plans / RI\n(60-70% of fleet)\nCommitted — 72% discount"]
        OD["On-Demand\n(10-20% of fleet)\nBuffer / safety margin"]
        SPOT["Spot Instances\n(10-30% of fleet)\nFault-tolerant overflow"]
    end

    RI --- OD --- SPOT

    style RI fill:#2d6a4f,color:#fff
    style OD fill:#1a535c,color:#fff
    style SPOT fill:#ff9f1c,color:#000
```

**Key rules:**
- **Base capacity** → Savings Plans (flexible across instance families, regions, even Fargate/Lambda)
- **Buffer** → On-Demand (no commitment, absorbs unexpected load)
- **Burst/batch** → Spot (90% savings, only for interruptible work)
- **Never run stateful workloads on Spot** — 2-minute termination notice isn't enough for DB flush

---

## Pricing Model Comparison

| Model | Discount | Commitment | Applies To |
|-------|---------|-----------|------------|
| **On-Demand** | 0% | None | EC2, Fargate, Lambda |
| **Savings Plans (Compute)** | Up to 72% | $/hr for 1 or 3 years | EC2 + Fargate + Lambda (all!) |
| **Savings Plans (EC2 Instance)** | Up to 72% | Locked to family + region | EC2 only |
| **Reserved Instances** | Up to 72% | 1 or 3 years, locked to type | EC2 only |
| **Spot** | Up to 90% | None, 2-min reclaim | EC2, Fargate Spot |

> **[SDE2 TRAP]** Compute Savings Plans are almost always better than RIs now because they apply across EC2, Fargate, AND Lambda. RIs only make sense if you're 100% locked into a specific instance type. Say this in interviews — it signals you understand modern cost optimization.

---

## ECS on EC2 vs Fargate — The Detailed Comparison

| Dimension | ECS on EC2 | Fargate |
|-----------|-----------|---------|
| Server management | You manage EC2 fleet | None — AWS manages |
| Pricing | Per-instance (even if idle) | Per-task (vCPU-sec + GB-sec) |
| Scaling | Scale instances + tasks separately | Just scale tasks |
| Startup time | Fast (task on existing host) | 30-60s (Firecracker microVM) |
| GPU support | ✅ | ❌ |
| Max resources | Limited by instance type | 16 vCPU / 120 GB |
| Networking | awsvpc, bridge, host modes | awsvpc only |
| Isolation | Process-level (shared kernel) | VM-level (Firecracker) |
| SSH / Debug | SSH into host, docker exec | ECS Exec (via SSM) |
| Persistent storage | EBS, instance store | EFS only (ephemeral default) |
| OS patching | You do it | AWS does it |
| Cost at scale | ✅ Cheaper (bin-packing + RIs) | More expensive |
| Cost at variable load | More expensive (idle capacity) | ✅ Cheaper (per-task) |

**Decision rule:** If utilization > 70% consistently → EC2 launch type. Below that → Fargate.

---

## Lambda vs Fargate — When to Pick Which

| Scenario | Lambda | Fargate |
|----------|--------|---------|
| Runtime < 15 min | ✅ | ✅ |
| Runtime > 15 min | ❌ | ✅ |
| Need > 10 GB RAM | ❌ | ✅ (up to 120 GB) |
| Need Docker ecosystem | ⚠️ (container images supported but limited) | ✅ Full Docker |
| Event-driven (S3, SQS, DynamoDB triggers) | ✅ Native triggers | ⚠️ Needs polling |
| HTTP API | ✅ via API Gateway / Function URLs | ✅ via ALB |
| Scale to zero | ✅ Native | ✅ (desired=0) |
| Cold start sensitivity | ⚠️ 100ms-10s | ⚠️ 30-60s |
| Sustained 1K+ RPS | ❌ Expensive | ✅ |
| Sidecar containers | ✅ (Lambda extensions, limited) | ✅ Full sidecar support |
| Complex deployment (blue/green, canary) | ⚠️ Lambda aliases + CodeDeploy | ✅ Full CodeDeploy |

---

## The Compute Decision Checklist (Use in System Design)

Before picking compute in any system design interview, walk through this flowchart:

```mermaid
flowchart TD
    Q1{"1️⃣ Execution duration\n> 15 minutes?"}
    Q1 -->|"Yes"| NOLAMBDA["❌ Eliminate Lambda"]
    Q1 -->|"No"| Q2
    NOLAMBDA --> Q2

    Q2{"2️⃣ Hard constraints?\nGPU / kernel / licensing"}
    Q2 -->|"Yes"| EC2_ONLY["✅ EC2 only\n(Dedicated Host if licensing)"]
    Q2 -->|"No"| Q3

    Q3{"3️⃣ Stateful?\n(in-memory cache, DB)"}
    Q3 -->|"Yes"| EC2_STATE["✅ EC2\n(persistent memory + EBS)"]
    Q3 -->|"No"| Q4

    Q4{"4️⃣ Traffic pattern?"}
    Q4 -->|"Spiky /\nevent-driven"| LAMBDA_WIN["✅ Lambda\n(pay per invocation)"]
    Q4 -->|"Variable"| FARGATE_WIN["✅ Fargate\n(per-task, no fleet mgmt)"]
    Q4 -->|"Steady 24/7"| Q5

    Q5{"5️⃣ Team size?"}
    Q5 -->|"Small / no DevOps"| FARGATE_WIN2["✅ Fargate\n(ops simplicity)"]
    Q5 -->|"Large / SRE team"| ECS_EC2_WIN["✅ ECS on EC2\n(RI + bin-packing)"]

    FINAL["6️⃣ ALWAYS propose HYBRID\nLambda events + Fargate APIs + EC2 stateful"]
    LAMBDA_WIN --> FINAL
    FARGATE_WIN --> FINAL
    FARGATE_WIN2 --> FINAL
    ECS_EC2_WIN --> FINAL

    style EC2_ONLY fill:#2d6a4f,color:#fff
    style EC2_STATE fill:#2d6a4f,color:#fff
    style LAMBDA_WIN fill:#ff9f1c,color:#000
    style FARGATE_WIN fill:#6a0572,color:#fff
    style FARGATE_WIN2 fill:#6a0572,color:#fff
    style ECS_EC2_WIN fill:#1a535c,color:#fff
    style FINAL fill:#d4a373,color:#000
```

---

## Senior-Level Gotchas

1. **"Just use Lambda for everything"** is a red flag. Interviewers want you to recognize Lambda's limits: 15-min timeout, cold starts, 10 GB memory cap, no GPU, expensive at sustained high RPS, hard to debug.

2. **"Just use Kubernetes"** is also a red flag unless justified. EKS has massive operational overhead. If you don't need multi-cloud portability or K8s-specific features (custom CRDs, Istio, Argo), ECS is simpler.

3. **Cost analysis without traffic pattern is meaningless.** "Lambda is cheaper" or "EC2 is cheaper" — both are wrong without context. Always ask about volume and pattern first.

4. **Fargate cold start is real.** ~30-60s to spin up (image pull + Firecracker boot). Keep images small (<200 MB), use ECR in the same region, and pre-provision tasks if latency-sensitive.

5. **Don't forget ECS Anywhere / Fargate on Outposts.** If asked about hybrid cloud (on-prem + AWS), ECS Anywhere runs ECS tasks on your own hardware. Niche but signals depth.

6. **Lambda@Edge / CloudFront Functions** exist for edge compute. If the workload is "transform HTTP requests at the CDN layer" or "A/B testing at the edge," this is the answer — not EC2 or Fargate.

7. **Savings Plans cover Lambda too.** Most candidates don't know this. Compute Savings Plans discount applies to Lambda duration charges. If you're running high-volume Lambda, this matters.

8. **The migration trap.** Never suggest rewriting a monolith to Lambda. The realistic path: EC2 → containerize (ECS) → decompose → selectively move event-driven pieces to Lambda over quarters, not weeks.

---

## Interview Cheat Sheet

- **Never answer "which compute?" without asking about traffic pattern, team size, and hard constraints first.**
- **Five axes:** workload profile, ops burden, cost structure, scaling behavior, hard constraints.
- **Lambda:** event-driven, <15 min, spiky/low traffic, scale-to-zero. Expensive at sustained high RPS.
- **Fargate:** containerized workloads, variable traffic, small teams, no GPU. Sweet spot for most microservices.
- **ECS on EC2:** large steady fleets, cost-optimized with RIs, GPU needs, maximum control.
- **Raw EC2:** stateful workloads (databases, caches), licensed software, kernel-level access.
- **Always propose a hybrid** in system design: Lambda for events + Fargate for APIs + EC2 for stateful.
- **Cost crossover:** Lambda → Fargate around ~1M req/day. Fargate → EC2 around >70% sustained utilization.
- **Migration path:** Monolith on EC2 → Containerize → Microservices → Selective Lambda.
- **EKS only when:** multi-cloud needed, K8s expertise exists on team, need K8s ecosystem (Istio, Argo, custom operators).
- **Savings Plans > Reserved Instances** for flexibility (applies to EC2 + Fargate + Lambda).
- **Spot Instances:** up to 90% off, 2-min reclaim, diversify across types/AZs, never for stateful workloads.

---

## Every System Design Must Address These 5 Compute Concerns

1. **Scaling strategy** — "Base on Savings Plans, buffer on On-Demand, burst on Spot/Fargate"
2. **Fault tolerance** — "Multi-AZ, health checks at every layer, circuit breakers on deploys"
3. **Cold start mitigation** — "Provisioned concurrency for Lambda, pre-provisioned tasks for Fargate, warm pools for EC2 ASGs"
4. **Cost optimization** — "Right-size instances, Savings Plans for base, Spot for batch, kill idle resources"
5. **Deployment safety** — "Blue/green via CodeDeploy, canary traffic shifting, automatic rollback on error rate spike"
