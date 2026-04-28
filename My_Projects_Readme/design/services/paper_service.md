# Paper Service — Deep Dive

> **One-liner**: The entry point for all papers into the system. Handles upload, DOI-based fetch, de-duplication, and orchestrates the async ingestion pipeline.

---

## 1. Architecture Overview

```mermaid
graph TB
    subgraph Clients
        UI["Web UI"]
        SDK["Python SDK"]
    end

    subgraph PaperService["Paper Service (Cloud Run)"]
        direction TB
        Upload["POST /papers/upload"]
        Fetch["POST /papers/fetch"]
        Get["GET /papers/:id"]
        List["GET /papers"]
        Delete["DELETE /papers/:id"]
        Extraction["GET /papers/:id/extraction"]

        subgraph Internal["Internal Components"]
            Dedup["De-Duplication Engine"]
            Hasher["Content Hasher (SHA-256)"]
            StatusMgr["Status Manager"]
        end
    end

    subgraph Dependencies
        PG["PostgreSQL\n(papers table)"]
        GCS["Cloud Storage\n(PDFs)"]
        PubSub["Pub/Sub\n(paper-ingestion topic)"]
        DL["Download Service\n(for DOI fetch)"]
    end

    Clients --> PaperService
    Upload --> Hasher --> Dedup
    Fetch --> Dedup
    Dedup --> PG
    Upload --> GCS
    PaperService --> PubSub
    Fetch --> DL

    style PaperService fill:#1e293b,color:#f8fafc
    style Internal fill:#334155,color:#f8fafc
    style Dedup fill:#3b82f6,color:#fff
    style Hasher fill:#8b5cf6,color:#fff
    style StatusMgr fill:#f59e0b,color:#000
```

---

## 2. What Exists vs What Changed

| Aspect | What Exists (Built at Infocusp) | Reimagined (v2) |
|--------|-------------------------------|-----------------|
| **Upload** | PDF upload → GCS → trigger Data Agent | Same, but with content hash de-dup layer added |
| **DOI fetch** | DOI → Download Service → GCS | Same, but with GCS cache check first (avoid re-download) |
| **De-duplication** | DOI match only | Two layers: DOI match (instant) + SHA-256 content hash (catches papers without DOIs) |
| **Status tracking** | Basic (pending/done) | Full state machine: `pending → processing → ready → unavailable` |
| **Extraction versioning** | Single extraction per paper | Versioned: v1, v2... with `is_latest` flag for model upgrades |
| **Storage** | GCS for PDFs and JSONs | Same — GCS for blobs, PostgreSQL for metadata + URIs |
| **Error handling** | Basic try/catch | Circuit breaker on Download Service, idempotent ingestion workers |

---

## 3. API Contract

### 3.1 Upload Paper (PDF)

```
POST /api/papers/upload
Content-Type: multipart/form-data

Body:
  file: <PDF binary>
  metadata (optional): {
    "doi": "10.1016/j.biortech.2020.123456",
    "title": "Biochar production from rice husk"
  }

Response (new paper):
  202 Accepted
  {
    "paper_id": "abc-123",
    "status": "processing",
    "message": "Paper accepted. Extraction in progress."
  }

Response (duplicate detected):
  200 OK
  {
    "paper_id": "existing-456",
    "status": "ready",
    "duplicate": true,
    "matched_by": "content_hash"  // or "doi"
  }

Errors:
  400 — Invalid file (not a PDF, corrupted)
  413 — File too large (>50MB)
  500 — GCS upload failed
```

### 3.2 Fetch Paper by DOI

```
POST /api/papers/fetch
Content-Type: application/json

Body:
  {
    "doi": "10.1016/j.biortech.2020.123456"
  }

Response (new paper):
  202 Accepted
  {
    "paper_id": "abc-123",
    "status": "processing",
    "message": "Download initiated. Extraction will follow."
  }

Response (already exists):
  200 OK
  {
    "paper_id": "existing-456",
    "status": "ready",
    "duplicate": true,
    "matched_by": "doi"
  }

Errors:
  404 — DOI not found in any source (OpenAlex, Sci-Hub)
  502 — All download sources failed
```

### 3.3 Get Paper

```
GET /api/papers/:id

Response:
  200 OK
  {
    "id": "abc-123",
    "doi": "10.1016/...",
    "title": "Biochar production...",
    "authors": [{"name": "Zhang, L.", "affiliation": "..."}],
    "abstract": "...",
    "publication_date": "2020-06-15",
    "journal": "Bioresource Technology",
    "source": "upload",
    "extraction_status": "ready",
    "has_pdf": true,
    "has_extraction": true,
    "extraction_version": 2,
    "created_at": "..."
  }
```

### 3.4 Get Latest Extraction

```
GET /api/papers/:id/extraction

Response:
  200 OK
  {
    "paper_id": "abc-123",
    "version": 2,
    "model_used": "gemini-2.0-flash",
    "download_url": "https://storage.googleapis.com/...?X-Goog-Signature=...",
    "expires_in": 3600,
    "summary": {
      "section_count": 8,
      "table_count": 3,
      "figure_count": 5,
      "reference_count": 42
    }
  }
```

> [!NOTE]
> The actual JSON extraction (50-500KB) is served via a **GCS signed URL** — not embedded in the API response. This keeps the API response lightweight and lets the client download the JSON directly from GCS at CDN speeds.

### 3.5 List Papers (Paginated)

```
GET /api/papers?page=1&per_page=20&status=ready&sort=created_at:desc

Response:
  200 OK
  {
    "papers": [...],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 142,
      "total_pages": 8
    }
  }
```

### 3.6 Delete Paper

```
DELETE /api/papers/:id

Response:
  204 No Content

Note: Soft delete — sets is_deleted = true.
GCS objects cleaned up via lifecycle policy after 30 days.
```

---

## 4. De-Duplication Engine — The Two-Layer System

This is the most important internal component. Without it, users upload the same paper repeatedly, wasting Gemini API calls ($0.10/paper).

### 4.1 Flow

```mermaid
flowchart TB
    Input["Incoming Paper\n(PDF upload or DOI fetch)"]

    Input --> HasDOI{"Has DOI?"}

    HasDOI -->|"Yes"| DOICheck["Layer 1: DOI Match\nSELECT id FROM papers WHERE doi = $1"]
    HasDOI -->|"No"| HashCheck

    DOICheck --> DOIFound{"Found?"}
    DOIFound -->|"Yes"| ReturnExisting["Return existing paper_id\n(matched_by: 'doi')"]
    DOIFound -->|"No"| HashCheck

    HashCheck["Layer 2: Content Hash\nSHA-256 of PDF bytes"]
    HashCheck --> ComputeHash["Compute SHA-256"]
    ComputeHash --> HashLookup["SELECT id FROM papers\nWHERE content_hash = $1"]
    HashLookup --> HashFound{"Found?"}
    HashFound -->|"Yes"| ReturnExisting2["Return existing paper_id\n(matched_by: 'content_hash')"]
    HashFound -->|"No"| NewPaper["New paper → proceed\nwith ingestion"]

    style Input fill:#1e293b,color:#f8fafc
    style ReturnExisting fill:#22c55e,color:#000
    style ReturnExisting2 fill:#22c55e,color:#000
    style NewPaper fill:#3b82f6,color:#fff
    style DOICheck fill:#8b5cf6,color:#fff
    style HashCheck fill:#f59e0b,color:#000
```

### 4.2 Why Two Layers?

| Layer | Speed | Catches | Misses |
|-------|-------|---------|--------|
| **DOI match** | O(1) — indexed lookup | Same paper fetched by different users, same paper from different sources | Papers without DOIs (preprints, user uploads) |
| **Content hash** (SHA-256) | O(1) — indexed lookup after hash computation | Papers without DOIs, papers with different DOIs for same content, same PDF uploaded by two users | Different PDF renderings of same paper (e.g., author copy vs publisher copy) |

> [!IMPORTANT]
> **Layer 1 is instant** (just a DB lookup). **Layer 2 requires reading the entire PDF** to compute the hash — still fast (milliseconds for a typical 2MB PDF), but we only do it if Layer 1 misses.

### 4.3 Race Condition Handling

Two users upload the same paper at the same time:

```sql
-- Uses ON CONFLICT to handle races
INSERT INTO papers (doi, title, content_hash, ...)
VALUES ($1, $2, $3, ...)
ON CONFLICT (doi) DO NOTHING
RETURNING id;

-- If RETURNING is empty → another request won the race
-- → SELECT the existing paper_id and return it
```

---

## 5. Paper Status — State Machine

```mermaid
stateDiagram-v2
    [*] --> pending : Paper created\n(stub or upload)

    pending --> processing : Ingestion worker\npicks up message

    processing --> ready : PDF downloaded +\nData Agent extraction +\nEmbeddings generated

    processing --> unavailable : Download failed\n(all sources exhausted)

    unavailable --> processing : Manual retry\nor new source added

    ready --> processing : Re-extraction triggered\n(model upgrade)

    ready --> [*] : Soft deleted

    note right of pending : Paper row exists in DB.\nNo PDF, no extraction yet.
    note right of processing : Worker is actively\ndownloading/extracting.
    note right of ready : PDF in GCS, JSON in GCS,\nembeddings in pgvector.\nFully searchable.
    note right of unavailable : Metadata from OpenAlex exists.\nNo PDF obtainable.\nCan still appear in search\nby title/abstract.
```

### Status Transitions (Who Triggers What)

| From | To | Triggered By | SQL |
|------|----|-------------|-----|
| `—` | `pending` | Paper Service (on upload/fetch) | `INSERT INTO papers (..., extraction_status='pending')` |
| `pending` | `processing` | Ingestion Worker (on Pub/Sub message) | `UPDATE papers SET extraction_status='processing' WHERE id=$1` |
| `processing` | `ready` | Ingestion Worker (after successful extraction) | `UPDATE papers SET extraction_status='ready' WHERE id=$1` |
| `processing` | `unavailable` | Ingestion Worker (download failed) | `UPDATE papers SET extraction_status='unavailable' WHERE id=$1` |
| `ready` | `processing` | Re-extraction API call | `UPDATE papers SET extraction_status='processing' WHERE id=$1` |

---

## 6. Ingestion Pipeline (Async Worker)

The Paper Service itself is a **thin HTTP handler**. The heavy lifting happens in the **Paper Ingestion Worker** — a Cloud Run Job triggered via Pub/Sub.

```mermaid
sequenceDiagram
    participant PS as Paper Service
    participant PubSub as Pub/Sub
    participant PIW as Ingestion Worker
    participant DL as Download Service
    participant OA as OpenAlex
    participant SH as Sci-Hub
    participant GCS as Cloud Storage
    participant DA as Data Agent
    participant Gemini as Vertex AI
    participant EmbSvc as Embedding Service
    participant PG as PostgreSQL

    PS->>PubSub: Publish {paper_id, doi, source}

    Note over PubSub,PIW: Async — worker picks up

    PubSub->>PIW: paper-ingestion message

    PIW->>PG: Idempotency check:\nSELECT extraction_status\nWHERE id = paper_id
    alt Already processed
        PIW->>PIW: Skip (idempotent)
    else Needs processing
        PIW->>PG: UPDATE status = 'processing'

        rect rgb(59, 130, 246, 0.1)
            Note over PIW,GCS: Phase 1: Get PDF
            alt PDF already in GCS (upload path)
                PIW->>GCS: PDF exists, skip download
            else DOI fetch path
                PIW->>DL: fetch_paper(doi)
                DL->>GCS: Check cache first
                alt Cache hit
                    GCS-->>DL: Cached PDF
                else Cache miss
                    DL->>OA: OpenAlex open access URL
                    alt Found
                        OA-->>DL: PDF URL
                        DL->>DL: Download PDF
                    else Not found
                        DL->>SH: Sci-Hub (if enabled)
                        alt Found
                            SH-->>DL: PDF bytes
                        else Not found
                            DL-->>PIW: DownloadError
                            PIW->>PG: UPDATE status = 'unavailable'
                            PIW->>PIW: Return early
                        end
                    end
                end
                DL-->>PIW: PDF bytes
                PIW->>GCS: Store PDF
                PIW->>PG: UPDATE pdf_gcs_uri
            end
        end

        rect rgb(168, 85, 247, 0.1)
            Note over PIW,Gemini: Phase 2: Extract (Data Agent)
            PIW->>DA: extract(paper_id, pdf_gcs_uri)
            DA->>Gemini: Multimodal PDF extraction
            Gemini-->>DA: Structured JSON
            DA->>GCS: Store JSON
            DA-->>PIW: json_gcs_uri
            PIW->>PG: INSERT paper_extraction
        end

        rect rgb(34, 197, 94, 0.1)
            Note over PIW,PG: Phase 3: Generate Embeddings
            PIW->>PIW: Chunk JSON into sections
            PIW->>EmbSvc: embed_batch(chunks)
            EmbSvc->>Gemini: Batch embedding
            Gemini-->>EmbSvc: 768-dim vectors
            EmbSvc-->>PIW: embeddings[]
            PIW->>PG: INSERT paper_chunks with vectors
        end

        PIW->>PG: UPDATE status = 'ready'
    end
```

### Worker Implementation

```python
async def paper_ingestion_worker(message):
    """
    Pub/Sub push handler. Idempotent — safe to retry.
    Phases: Download PDF → Data Agent → Embeddings → Mark Ready
    """
    payload = json.loads(message.data)
    paper_id = payload["paper_id"]
    doi = payload.get("doi")
    source = payload["source"]  # 'upload' or 'doi_fetch'

    # ── Idempotency check ──
    paper = await db.fetchrow(
        "SELECT extraction_status, pdf_gcs_uri FROM papers WHERE id = $1",
        paper_id
    )
    if paper["extraction_status"] in ("ready", "processing"):
        message.ack()
        return  # already handled or being handled

    await db.execute(
        "UPDATE papers SET extraction_status = 'processing' WHERE id = $1",
        paper_id
    )

    # ── Phase 1: Get PDF ──
    pdf_gcs_uri = paper["pdf_gcs_uri"]
    if not pdf_gcs_uri:
        try:
            pdf_gcs_uri = await download_service.fetch(doi)
            await db.execute(
                "UPDATE papers SET pdf_gcs_uri = $1 WHERE id = $2",
                pdf_gcs_uri, paper_id
            )
        except DownloadError:
            await db.execute(
                "UPDATE papers SET extraction_status = 'unavailable' WHERE id = $1",
                paper_id
            )
            message.ack()
            return

    # ── Phase 2: Data Agent Extraction ──
    json_gcs_uri = await data_agent.extract(paper_id, pdf_gcs_uri)
    await db.execute("""
        UPDATE paper_extractions SET is_latest = FALSE
        WHERE paper_id = $1 AND is_latest = TRUE
    """, paper_id)
    await db.execute("""
        INSERT INTO paper_extractions (paper_id, version, json_gcs_uri, model_used, is_latest)
        VALUES ($1, (SELECT COALESCE(MAX(version),0)+1 FROM paper_extractions WHERE paper_id=$1),
                $2, $3, TRUE)
    """, paper_id, json_gcs_uri, "gemini-2.0-flash")

    # ── Phase 3: Embeddings ──
    paper_json = await gcs.download_json(json_gcs_uri)
    chunks = chunk_paper_json(paper_json)  # split into ~500-token sections
    embeddings = await embedding_service.embed_batch([c.text for c in chunks])
    await store_chunks_with_embeddings(paper_id, chunks, embeddings)

    # ── Done ──
    await db.execute(
        "UPDATE papers SET extraction_status = 'ready' WHERE id = $1",
        paper_id
    )
    message.ack()
```

---

## 7. GCS Bucket Layout

```
gs://paper-extraction-prod/
├── papers/
│   ├── {paper_id}/
│   │   └── original.pdf              ← Raw uploaded/downloaded PDF
│   └── by-doi/
│       └── {url_encoded_doi}.pdf      ← DOI-keyed cache (for Download Service)
│
├── extractions/
│   └── {paper_id}/
│       ├── v1.json                    ← Data Agent output v1
│       └── v2.json                    ← Re-extraction with newer model
│
└── jobs/
    └── {job_id}/
        └── result.json                ← Aggregated multi-paper result
```

---

## 8. Database Tables Owned

The Paper Service **owns** (reads + writes):

```sql
-- Primary table
papers (id, doi, title, authors, abstract, publication_date, journal,
        source, pdf_gcs_uri, content_hash, extraction_status, ...)

-- Written by Ingestion Worker
paper_extractions (id, paper_id, version, json_gcs_uri, model_used,
                   is_latest, ...)

-- Written by Ingestion Worker
paper_chunks (id, paper_id, chunk_index, chunk_text, section, embedding)
```

**Other services read but don't write** to these tables.

---

## 9. Dependencies

```mermaid
flowchart LR
    PS["Paper Service"]
    PS --> PG["PostgreSQL\n(papers, extractions, chunks)"]
    PS --> GCS["Cloud Storage\n(PDFs, JSONs)"]
    PS --> PubSub["Pub/Sub\n(paper-ingestion topic)"]
    PS --> DL["Download Service\n(for DOI fetch)"]

    subgraph "Ingestion Worker (async)"
        PIW["Worker"]
        PIW --> DA["Data Agent\n(Gemini)"]
        PIW --> Emb["Embedding Service\n(Gemini)"]
    end

    PS -.->|"triggers via Pub/Sub"| PIW

    style PS fill:#3b82f6,color:#fff
    style PIW fill:#8b5cf6,color:#fff
```

---

## 10. Failure Modes & Recovery

| Failure | Impact | Detection | Recovery |
|---------|--------|-----------|----------|
| **GCS upload fails** | PDF not stored | Worker catches exception | Retry 3× → nack message → Pub/Sub redelivers |
| **Download Service: all sources fail** | No PDF obtainable | `DownloadError` raised | Mark paper `unavailable`. User notified. Can retry later if new source added |
| **Data Agent (Gemini) timeout** | No JSON extraction | Worker timeout after 5 min | Retry with exponential backoff (3 attempts). If all fail → nack → DLQ |
| **Embedding Service fails** | No vector chunks | Worker catches exception | Paper still marked `ready` but without embeddings → not searchable. Background job can backfill later |
| **PostgreSQL connection fail** | Can't update status | Connection pool error | Cloud SQL Proxy auto-reconnects. Worker retries. If persistent → circuit breaker → nack |
| **Pub/Sub duplicate message** | Worker runs twice for same paper | Idempotency check at start | `SELECT extraction_status` → skip if already `processing` or `ready` |
| **Worker OOM crash** | Mid-processing crash | Pub/Sub ack timeout | Message redelivered. Idempotent worker picks up safely |
| **Two users upload same paper simultaneously** | Race condition on INSERT | `ON CONFLICT DO NOTHING` | Second request gets existing paper_id |

---

## 11. Key Design Decisions

| Decision | What We Chose | Alternative | Why |
|----------|--------------|-------------|-----|
| **Two-layer de-dup** | DOI + SHA-256 hash | DOI only | Many papers lack DOIs (preprints, user uploads). Content hash catches these |
| **Async ingestion** | Pub/Sub → Worker | Synchronous in API handler | Extraction takes 30s-5min. Can't block the HTTP response |
| **Soft delete** | `is_deleted` flag | Hard delete | GCS objects need lifecycle cleanup. Allows undo within 30 days |
| **Signed URLs for extraction JSON** | GCS signed URL in response | Embed JSON in API response | JSONs are 50-500KB. Signed URL serves from CDN, keeps API response small |
| **Extraction versioning** | Version column + `is_latest` flag | Overwrite old extraction | Models improve — need history for comparison and rollback |
| **Status as column** | `extraction_status` on papers table | Separate status table | One fewer join. Status is always read with the paper |
| **Content hash on full PDF** | SHA-256 of entire file | Hash of first N bytes | Slight speed cost but guarantees uniqueness. Prevents collisions from shared headers |
