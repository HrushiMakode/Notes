# AWS DynamoDB — NoSQL Foundations & Data Model

## Why NoSQL?

Relational DBs normalize data and JOIN at read time. This breaks at scale:

1. **JOINs collapse** — multi-table JOIN across millions of rows = timeout
2. **Vertical scaling ceiling** — you can't buy an infinitely big machine
3. **Schema rigidity** — `ALTER TABLE` on a billion-row production table is an operational nightmare

**NoSQL flips the contract:** model data around your **access patterns**, not around normalization. Trade ad-hoc query flexibility for predictable performance at any scale.

---

## CAP Theorem

Every distributed database guarantees at most **2 of 3**: Consistency, Availability, Partition Tolerance.

Network partitions are unavoidable, so the real choice is:

| Choice | Tradeoff | Examples |
|--------|----------|----------|
| **CP** | Might reject requests during partition | HBase, MongoDB (strict mode) |
| **AP** | Always responds, data might be stale | Cassandra, **DynamoDB (default)** |

> **DynamoDB is AP by default** (eventually consistent reads), but gives you a **per-request dial** to opt into strong consistency.

---

## DynamoDB's Origin & Philosophy

Born from Amazon's **Dynamo paper (2007)** — the system behind the shopping cart during Black Friday. Core guarantees:

1. **Predictable single-digit ms latency** at any scale
2. **Fully managed** — zero servers, zero patching
3. **Schemaless** — items can have different attributes (except the key)
4. **HTTP API** — no persistent connections, no connection pool tuning
5. **Key-value + document** database — not purely key-value, not purely document

---

## Core Data Model

Think of a DynamoDB table as a **filing cabinet**:

```
FILING CABINET = Table ("Orders")
│
├── DRAWER (Partition) ← determined by Partition Key hash
│   ├── FOLDER: PK="USER#101", SK="ORDER#2024-01-15" → {amount: 59.99, status: "shipped"}
│   ├── FOLDER: PK="USER#101", SK="ORDER#2024-03-22" → {amount: 120.00, status: "delivered"}
│   └── (folders sorted by Sort Key within the drawer)
│
├── DRAWER (Partition)
│   └── FOLDER: PK="USER#202", SK="ORDER#2024-02-10" → {amount: 34.50, status: "pending"}
│
└── DRAWER (Partition)
    └── FOLDER: PK="USER#303", SK="ORDER#2024-04-01" → {amount: 89.00, items: ["book","pen"]}
```

### Terminology Mapping

| DynamoDB Term | RDBMS Equivalent | What It Is |
|---|---|---|
| **Table** | Table | Container for all data |
| **Item** | Row | A single record (max **400 KB**) |
| **Attribute** | Column | A field — NOT enforced, each item can have different attributes |
| **Partition Key (PK)** | — | Hash key. Determines WHICH partition stores the item. **Equality lookups only.** |
| **Sort Key (SK)** | — | Optional. Orders items WITHIN a partition. Enables range queries (`begins_with`, `between`). |
| **Primary Key** | Primary Key | Either PK alone (simple) or PK + SK (composite). Must be unique per item. |

### Two Primary Key Types

**Simple Primary Key** — PK only. Each PK value = exactly one item.
> Use when: each item is uniquely identified by one value (e.g., `user_id`).

**Composite Primary Key** — PK + SK. The *combination* must be unique.
> Use when: multiple related items under one partition (e.g., all orders for a user, sorted by date).

### Data Types

DynamoDB's own type system: `S` (String), `N` (Number), `B` (Binary), `BOOL`, `NULL`, `L` (List), `M` (Map), `SS`/`NS`/`BS` (Sets). Numbers are sent as strings over the wire but compared numerically.

---

## ⚠️ Gotchas & Edge Cases

1. **400 KB item size limit** — hard wall, no exceptions. Large blobs → S3.
2. **Schemaless ≠ schema-free** — no `NOT NULL`, no FK, no constraints. App must enforce integrity.
3. **Cannot change primary key after table creation.** Wrong key = delete and recreate.
4. **Empty strings allowed** (since 2020), but **empty Sets are NOT.**
5. **[SDE2 TRAP]** PK ≠ Primary Key when you have a Sort Key. PK alone does NOT need to be unique in composite keys — only the **PK+SK combination** must be unique.

---

## 📌 Interview Cheat Sheet

- DynamoDB = **fully managed, key-value + document** NoSQL database (AP system, CAP theorem)
- Primary key: **simple (PK)** or **composite (PK + SK)** — know the difference cold
- PK = **partition placement** (hash), SK = **sort order within partition**
- Max item size: **400 KB**. Max table size: **unlimited**
- HTTP-based API — scales naturally with Lambda (no connection pooling)
- "When NOT to use DynamoDB?" → complex ad-hoc queries, heavy JOINs, unknown access patterns upfront
