# Paper Extraction System — Reimagined on GCP (Part 1)

> A ground-up redesign of the Research Paper Data Extraction Engine, with detailed tradeoff analysis for every major architectural decision.

---

## 1. High-Level Architecture

```mermaid
graph TB
    subgraph Clients["Client Layer"]
        WebUI["Web UI (React)"]
        SDK["Python SDK / CLI"]
    end

    subgraph Edge["Edge / Gateway"]
        LB["Cloud Load Balancer"]
        API["API Gateway (Cloud Run)"]
    end

    subgraph Core["Core Services (Cloud Run)"]
        PS["Paper Service"]
        ES["Extraction Service"]
        CS["Citation Service"]
        SS["Search Service"]
    end

    subgraph Async["Async Processing"]
        PubSub["Cloud Pub/Sub"]
        Workers["Worker Pool (Cloud Run Jobs)"]
    end

    subgraph AI["AI Layer"]
        DA["Data Agent"]
        GK["Gatekeeper Filter"]
        EmbSvc["Embedding Service"]
        VertexAI["Vertex AI (Gemini)"]
    end

    subgraph Data["Data Layer"]
        PG["Cloud SQL (PostgreSQL 15 + pgvector)"]
        GCS["Cloud Storage (PDFs + JSONs)"]
        Redis["Memorystore (Redis)"]
    end

    subgraph External["External APIs"]
        OA["OpenAlex"]
        SH["Sci-Hub Wrapper"]
    end

    Clients --> LB --> API
    API --> Core
    PS --> GCS & PG
    PS --> PubSub
    ES --> PubSub
    CS --> OA & PG & Redis
    SS --> PG
    Workers --> PubSub
    Workers --> VertexAI
    Workers --> GCS & PG
    DA --> VertexAI
    GK --> EmbSvc --> VertexAI
    GK --> Redis
    PS --> SH & OA
```

### Core Principle: **Services are Thin Orchestrators, Workers Do Heavy Lifting**

Every Cloud Run service is a lightweight HTTP handler that validates, orchestrates, and delegates. All expensive work (LLM calls, PDF processing, embedding) happens in async workers via Pub/Sub.

---

## 2. Tradeoff Discussions

### 2.1 Database: PostgreSQL (Cloud SQL) vs Alternatives

#### Candidates Evaluated

| | **Cloud SQL (PG 15 + pgvector)** | **Firestore** | **AlloyDB** | **Cloud Spanner** |
|---|---|---|---|---|
| **Model** | Relational | Document (NoSQL) | PostgreSQL-compatible | Globally distributed relational |
| **Joins** | ✅ Native SQL joins | ❌ No joins — denormalize or fan-out reads | ✅ Full SQL | ✅ Full SQL |
| **Vector search** | ✅ pgvector (HNSW/IVFFlat) | ❌ None — need separate service | ✅ pgvector compatible | ❌ No native vector |
| **Citation graph queries** | ✅ Recursive CTEs | ❌ Extremely painful | ✅ Recursive CTEs | ✅ But expensive |
| **Schema flexibility** | Rigid schema + JSONB for flexible parts | ✅ Schemaless | Same as PG | Rigid |
| **Scaling** | Vertical (read replicas for reads) | ✅ Auto-scales horizontally | Auto-scales reads | ✅ Horizontal + global |
| **Cost (small-medium)** | **~$70/mo** | ~$30/mo | ~$200/mo | ~$500/mo minimum |
| **Operational burden** | Medium (backups, connections) | Low (managed) | Low-Medium | Low |

#### Why We Chose PostgreSQL (Cloud SQL)

```
The system has THREE data patterns that drive this decision:

1. RELATIONAL — Papers → Extractions → Jobs → Results
   → Need JOINs, foreign keys, transactions
   → Firestore: painful (fan-out reads, no joins)
   → PostgreSQL: natural fit

2. GRAPH — Citation network (paper A cites B cites C)
   → Need recursive CTEs for N-hop traversal
   → Firestore: impossible without external graph DB
   → PostgreSQL: WITH RECURSIVE works perfectly

3. VECTOR — Semantic search over paper chunks
   → Need cosine similarity on 768-dim embeddings
   → Firestore: need separate Vertex AI Vector Search ($200+/mo)
   → PostgreSQL: pgvector handles this in-DB
```

> [!IMPORTANT]
> **PostgreSQL handles all three patterns in ONE database.** This avoids the operational complexity of running Firestore + a graph DB + a vector DB separately.

#### Why NOT AlloyDB or Spanner?

- **AlloyDB**: Better performance than Cloud SQL, but **3x the cost** (~$200/mo). Our scale (< 100K papers) doesn't justify it. If we hit performance walls with Cloud SQL, AlloyDB is a drop-in upgrade path.
- **Spanner**: Global distribution is irrelevant (single-region app). Minimum ~$500/mo. Massive overkill.

#### The Firestore Migration Story

```mermaid
flowchart LR
    subgraph Before["Before (What Exists)"]
        FS["Firestore"]
        FS1["papers collection"]
        FS2["extractions collection"]
        FS3["No citation graph"]
        FS4["No vector search"]
    end

    subgraph After["After (Reimagined)"]
        PG["PostgreSQL"]
        PG1["papers table + FTS index"]
        PG2["paper_extractions + GCS URIs"]
        PG3["citations table + recursive CTEs"]
        PG4["paper_chunks + pgvector HNSW"]
    end

    Before -->|"Dual-write migration\n(2-3 weeks)"| After
```

---

### 2.2 Async Framework: Do API (Custom) vs Cloud Tasks vs Eventarc

This is the most consequential architecture decision. The existing system uses a **custom Do API** built on Pub/Sub with reply topics. Let's evaluate whether to keep it.

#### What the Do API Does Today

```
Client code:
  result = await Task('DataAgent_Worker').Do(payload)

Under the hood:
  1. Client creates ephemeral reply topic
  2. Publishes payload to worker's task topic
  3. Worker processes, publishes result to reply topic
  4. Client receives result
  5. Reply topic cleaned up
```

This gives **synchronous await semantics over an async Pub/Sub backbone**.

#### Candidates

| | **Do API (Custom Pub/Sub)** | **Cloud Tasks** | **Eventarc + Workflows** | **Pub/Sub (raw, no reply)** |
|---|---|---|---|---|
| **Request-Reply** | ✅ Built-in (reply topics) | ❌ Fire-and-forget only | ⚠️ Via Workflows state | ❌ Fire-and-forget |
| **Fan-Out + Collect** | ✅ `Task.Do([p1,p2,...])` | ❌ No result aggregation | ⚠️ Complex workflow DSL | ❌ Manual aggregation |
| **Back-pressure** | ⚠️ Manual | ✅ Rate limiting built-in | ✅ Managed | ❌ Manual |
| **Dead Letter Queue** | ⚠️ Manual setup | ✅ Built-in | ✅ Built-in | ✅ Pub/Sub DLQ |
| **Observability** | ⚠️ Custom logging | ✅ Cloud Console | ✅ Cloud Console | ⚠️ Custom |
| **Vendor lock-in** | Low (Pub/Sub is standard) | High (GCP-specific) | High | Low |
| **Complexity** | High (you maintain it) | Low | Medium | Low |
| **Cost** | Pub/Sub pricing only | Pub/Sub + Tasks pricing | Higher (Workflows billing) | Pub/Sub only |

#### Decision: Keep Do API, But Harden It

```mermaid
flowchart TB
    subgraph DoAPIv2["Do API v2 (Hardened)"]
        Client["Client: await Task.Do(payload)"]
        Client --> Publish["Publish to task topic\n+ attach reply_topic + correlation_id"]
        Publish --> Worker["Worker processes"]
        Worker --> Reply["Publish result to reply topic"]
        Reply --> Client

        subgraph New["New in v2"]
            DLQ["Dead Letter Queue\n(after 3 retries)"]
            Timeout["Per-task timeout\n(configurable)"]
            Partial["Partial results on\nfan-out failure"]
            Metrics["Cloud Monitoring\nintegration"]
        end

        Worker -->|"3 failures"| DLQ
        Client --> Timeout
        Client --> Partial
        Worker --> Metrics
    end
```

> [!TIP]
> **Why not switch to Cloud Tasks?** The killer feature of Do API is **request-reply with fan-out aggregation**. Cloud Tasks is fire-and-forget — you'd need to build a separate results-collection layer (polling DB, callbacks, etc.), which recreates Do API's complexity anyway.

#### What We ADD to Do API v2

| Enhancement | Why |
|---|---|
| **Dead Letter Queue** | Failed messages after 3 retries go to DLQ topic instead of being lost |
| **Per-task timeout** | Workers that hang don't block the entire fan-out |
| **Partial results** | If 3/50 workers fail, return 47 results + 3 errors instead of failing everything |
| **Correlation IDs** | Trace a request from API → Pub/Sub → Worker → Reply across Cloud Logging |
| **Cloud Monitoring metrics** | `do_api_tasks_total`, `do_api_task_duration_seconds`, `do_api_failures_total` |

---

### 2.3 Compute: Cloud Run vs GKE vs Cloud Functions

| | **Cloud Run (services)** | **Cloud Run Jobs** | **GKE Autopilot** | **Cloud Functions** |
|---|---|---|---|---|
| **Use case** | HTTP services | Batch / async workers | Full container orchestration | Single-function triggers |
| **Scale to zero** | ✅ | ✅ | ❌ (min node pool) | ✅ |
| **Max timeout** | 60 min | 24 hours | Unlimited | 9 min (gen2) |
| **Concurrency** | Up to 1000 req/instance | 1 task/instance | Configurable | 1 req/instance |
| **GPU** | ❌ | ❌ | ✅ | ❌ |
| **Cost at low scale** | **Very low** (pay per request) | **Very low** | ~$70+/mo minimum | Very low |
| **Startup time** | ~1-3s cold start | ~5-10s | N/A (always running) | ~1-5s |

#### Decision: Cloud Run Services + Cloud Run Jobs

```mermaid
flowchart TB
    subgraph Services["Cloud Run Services (HTTP, auto-scale)"]
        API["API Gateway"]
        PS["Paper Service"]
        ES["Extraction Service"]
        CS["Citation Service"]
        SS["Search Service"]
    end

    subgraph Jobs["Cloud Run Jobs (Long-running, Pub/Sub triggered)"]
        DAW["Data Agent Worker\n(PDF→JSON, up to 5 min)"]
        PEW["Prompt Extractor Worker\n(JSON+prompt→result, ~30s)"]
        PIW["Paper Ingestion Worker\n(Download+Extract+Embed)"]
        CTW["Citation Traversal Worker\n(BFS per level)"]
    end

    Services -->|"Pub/Sub"| Jobs
```

> [!NOTE]
> **Why not GKE?** Scale-to-zero is critical for cost. At our scale (< 1000 requests/day), GKE's minimum node pool cost exceeds Cloud Run's entire bill. GKE becomes relevant at >10K concurrent extractions.
>
> **Why not Cloud Functions?** The 9-minute timeout is too short for Data Agent extraction (can take 5+ min for large papers). Cloud Run Jobs support 24-hour timeouts.

---

### 2.4 Search: pgvector vs Vertex AI Vector Search vs Elasticsearch

| | **pgvector (in PostgreSQL)** | **Vertex AI Vector Search** | **Elasticsearch** |
|---|---|---|---|
| **Setup** | `CREATE EXTENSION vector;` | Managed index + endpoint | Self-managed or Elastic Cloud |
| **Latency (10K vectors)** | ~5-15ms | ~2-5ms | ~5-10ms |
| **Latency (1M vectors)** | ~50-100ms | ~5-10ms | ~10-20ms |
| **Full-text search** | ✅ Same DB (tsvector) | ❌ Separate service needed | ✅ Native |
| **Hybrid search** | ✅ SQL JOIN of vector + FTS | ❌ Manual fusion | ✅ Native |
| **Operational cost** | **$0 extra** (in existing PG) | ~$200/mo (always-on endpoint) | ~$150/mo |
| **Filter + search** | ✅ SQL WHERE clauses | ⚠️ Pre/post-filtering | ✅ Native |
| **Max scale** | ~5M vectors comfortable | 100M+ | 100M+ |

#### Decision: pgvector

At our scale (< 500K chunks across < 100K papers), pgvector with HNSW indexing handles everything. The killer advantage is **hybrid search in a single SQL query** — join vector similarity with full-text ranking and metadata filters, all in one round-trip.

If we grow past 1M papers, Vertex AI Vector Search is the upgrade path.

---

### 2.5 Cache Layer: Memorystore Redis vs Memcached

| | **Memorystore (Redis)** | **Memorystore (Memcached)** |
|---|---|---|
| **Data structures** | SET, HASH, SORTED SET, LIST | Key-Value only |
| **Persistence** | Optional (RDB/AOF) | None |
| **Use: Cycle detection** | ✅ `SADD citation:visited:{job_id} doi` | ❌ No SET type |
| **Use: Embedding cache** | ✅ `SET embed:{hash} [vector]` | ✅ Same |
| **Use: Rate limiting** | ✅ `INCR` + `EXPIRE` | ❌ No atomic incr+expire |
| **Use: Job progress** | ✅ `HSET job:{id} completed 5` | ❌ No HASH |
| **Cost** | ~$30/mo (1GB basic) | ~$20/mo |

#### Decision: Redis (Memorystore)

The SET data structure for cycle detection and HASH for job progress tracking are essential. Memcached can't do either.

#### Redis Key Design

```
citation:visited:{job_id}     → SET of OpenAlex IDs       TTL: 24h
embed:{text_hash}             → STRING (JSON float array)  TTL: 7d
citation:cache:{doi}          → HASH {refs, citers, ts}    TTL: 24h
ratelimit:openalex:{minute}   → INT (request count)        TTL: 60s
job:progress:{job_id}         → HASH {total, completed, failed}  TTL: 48h
```

---

### 2.6 LLM Integration: Vertex AI vs Direct Gemini API

| | **Vertex AI (Gemini)** | **Direct Gemini API (ai.google.dev)** |
|---|---|---|
| **Auth** | Service account (IAM) | API key |
| **VPC access** | ✅ Private endpoint | ❌ Public internet |
| **Model garden** | ✅ All models + fine-tuning | Limited |
| **Grounding** | ✅ Google Search grounding | ❌ |
| **Batch API** | ✅ (cheaper, async) | ❌ |
| **Pricing** | Same or cheaper (committed use) | Pay-as-you-go |
| **Observability** | ✅ Cloud Monitoring integration | Manual |

#### Decision: Vertex AI

Running on GCP, Vertex AI gives us IAM-based auth (no API key management), VPC-native access, and the **Batch Prediction API** for high-volume extractions at reduced cost.

---

## 3. Data Flow Architecture

### 3.1 Paper Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant API as API Gateway
    participant PS as Paper Service
    participant PG as PostgreSQL
    participant GCS as Cloud Storage
    participant PubSub as Pub/Sub
    participant PIW as Ingestion Worker
    participant DL as Download Service
    participant DA as Data Agent
    participant Gemini as Vertex AI
    participant EmbSvc as Embedding Service

    User->>API: POST /papers (PDF upload or DOI)

    alt PDF Upload
        API->>PS: upload(file)
        PS->>PS: SHA-256 content hash
        PS->>PG: Check content_hash exists?
        alt Duplicate
            PG-->>PS: Existing paper_id
            PS-->>API: 200 OK paper_id status duplicate
        else New
            PS->>GCS: Store PDF
            PS->>PG: INSERT paper status pending
            PS->>PubSub: Publish to paper-ingestion topic
            PS-->>API: 202 Accepted paper_id processing
        end
    else DOI Fetch
        API->>PS: fetch(doi)
        PS->>PG: Check DOI exists?
        alt Exists
            PG-->>PS: Existing paper_id
            PS-->>API: 200 OK paper_id
        else New
            PS->>PG: INSERT stub paper
            PS->>PubSub: Publish to paper-ingestion topic
            PS-->>API: 202 Accepted paper_id processing
        end
    end

    Note over PubSub,PIW: Async Processing via Worker

    PubSub->>PIW: paper-ingestion message
    PIW->>DL: Download PDF
    DL-->>PIW: PDF bytes
    PIW->>GCS: Store PDF
    PIW->>DA: Extract PDF to JSON
    DA->>Gemini: Multimodal extraction
    Gemini-->>DA: Structured JSON
    DA->>GCS: Store JSON
    PIW->>PG: INSERT paper_extraction record
    PIW->>EmbSvc: Generate chunk embeddings
    EmbSvc->>Gemini: Batch embed
    Gemini-->>EmbSvc: 768-dim vectors
    EmbSvc->>PG: INSERT paper_chunks with vectors
    PIW->>PG: UPDATE paper status ready
```

### 3.2 Multi-Paper Extraction Flow (Schema-First)

```mermaid
sequenceDiagram
    actor User
    participant API
    participant ES as Extraction Service
    participant Gemini as Vertex AI
    participant PG as PostgreSQL
    participant PubSub as Pub/Sub
    participant PEW as Prompt Extractor Workers
    participant GCS

    User->>API: POST /jobs with paper_ids and prompt
    API->>ES: create_job

    rect rgb(59, 130, 246, 0.1)
        Note over ES,Gemini: Step 1 - Schema Generation
        ES->>Gemini: Generate canonical schema for prompt
        Gemini-->>ES: fields with name type unit
        ES->>PG: Store schema in extraction_jobs
    end

    rect rgb(249, 115, 22, 0.1)
        Note over ES,PG: Step 2 - Relevance Filter
        ES->>PG: Cosine sim of prompt vs paper_chunks
        PG-->>ES: Relevant paper_ids above 0.6
    end

    rect rgb(34, 197, 94, 0.1)
        Note over ES,GCS: Step 3 - Ensure Paper JSONs Exist
        ES->>PG: Which papers have latest extraction?
        PG-->>ES: 12 ready and 6 missing
        ES->>PubSub: Trigger Data Agent for 6 missing
    end

    rect rgb(168, 85, 247, 0.1)
        Note over ES,PEW: Step 4 - Fan-Out Extraction
        ES->>PubSub: Do API fan-out 19 papers
        PubSub->>PEW: 19 parallel messages
        PEW->>GCS: Load paper JSON
        PEW->>Gemini: Extract per schema
        Gemini-->>PEW: Structured result
        PEW->>PG: Store extraction_job_result
        PEW-->>ES: Results collected via reply topics
    end

    rect rgb(236, 72, 153, 0.1)
        Note over ES: Step 5 - Programmatic Merge
        ES->>ES: Validate and normalize and dedup
        ES->>GCS: Store result.json
        ES->>PG: UPDATE job status completed
    end

    ES-->>API: job_id
    API-->>User: 202 Accepted with job_id
```

### 3.3 Citation Discovery Flow

```mermaid
sequenceDiagram
    participant ES as Extraction Service
    participant CS as Citation Service
    participant OA as OpenAlex
    participant Redis
    participant GK as Gatekeeper
    participant Gemini as Vertex AI
    participant PG as PostgreSQL

    ES->>CS: traverse seed_doi prompt depth 2
    CS->>Gemini: Embed prompt and cache in Redis

    rect rgb(59, 130, 246, 0.1)
        Note over CS,OA: BFS Level 0 - Seed
        CS->>OA: GET works by seed DOI
        OA-->>CS: referenced_works and cited_by
        CS->>OA: GET citers paginated limit 50
        OA-->>CS: 45 candidates total
        CS->>Redis: SADD visited set with seed_oa_id
    end

    rect rgb(249, 115, 22, 0.1)
        Note over CS,Redis: Gatekeeper Filter Level 0 to 1
        CS->>Redis: SISMEMBER visited set check
        Redis-->>CS: not visited
        CS->>GK: Check relevance of title and abstract
        GK->>Gemini: Embed candidate text
        Gemini-->>GK: candidate_embedding
        GK->>GK: cosine_sim check threshold 0.6
        GK-->>CS: ACCEPT or REJECT
        CS->>Redis: SADD visited set with candidate
        Note over CS: 45 candidates to 18 accepted 27 pruned
    end

    CS->>PG: Resolve 18 papers create stubs if needed
    CS->>PG: Store citation edges

    rect rgb(34, 197, 94, 0.1)
        Note over CS,OA: BFS Level 1 to 2 repeat
        Note over CS: Expand 18 papers ~720 candidates
        Note over CS: Gatekeeper prunes to ~60 accepted
    end

    CS->>Redis: EXPIRE visited set 24 hours
    CS-->>ES: paper_ids edges and stats
```

---

> [!NOTE]
> **Part 2** will cover: detailed component designs, full PostgreSQL schema, failure handling & circuit breakers, observability stack, security (IAM + VPC), and cost analysis.

**Ready for Part 2? Or want to discuss any of these tradeoffs first?**
