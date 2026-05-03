# AWS DynamoDB — Read & Write Operations + Consistency

## Single-Item Operations (Require Full Primary Key)

| Operation | What It Does | Key Behavior |
|-----------|-------------|--------------|
| `GetItem` | Read one item | Must provide full PK (+ SK if composite). Returns whole item or projected attributes. |
| `PutItem` | Create or **replace** an entire item | If PK+SK exists, **overwrites the entire item** — not a merge! |
| `UpdateItem` | Modify specific attributes | Creates item if it doesn't exist (upsert). Only touches specified attributes. |
| `DeleteItem` | Remove one item | Succeeds silently even if item doesn't exist. |

> **[SDE2 TRAP]** `PutItem` replaces the ENTIRE item. Old item had 10 attributes, you `PutItem` with 3 → you lost 7. `UpdateItem` surgically modifies only what you specify.

---

## Multi-Item Read Operations

| Operation | What It Does | When to Use |
|-----------|-------------|-------------|
| `Query` | Reads items from **one partition** | You know the PK. Use SK conditions to filter/sort. |
| `Scan` | Reads **every item in the entire table** | Don't know the PK. Last resort — burns RCU. |

### Query vs Scan — The Critical Distinction

```
Query:  "Go to drawer USER#alice, pull folders where SK begins_with ORDER#2024"
         → Opens ONE drawer, reads a few folders. Fast. Cheap.

Scan:   "Open EVERY drawer, look at EVERY folder, check if status = shipped"
         → Touches the ENTIRE table. Slow. Gets worse as table grows.
```

**Query SK conditions:** `=`, `<`, `>`, `<=`, `>=`, `between`, `begins_with`
**Cannot use on SK:** `contains`, `not_equals` — those are filter expressions only.

### Filter Expressions — The Misconception

Filters are applied **AFTER** data is read from disk. They reduce what's returned to your app, but **you still pay RCU for everything read.** Filters save bandwidth, NOT throughput cost.

> A `Scan` with `FilterExpression = "status = shipped"` on a 50 GB table reads ALL 50 GB and charges you for it.

---

## Consistency Models

DynamoDB replicates across **3 Availability Zones**:

```
Write arrives
     │
     ▼
┌─────────┐     replication     ┌─────────┐     replication     ┌─────────┐
│ LEADER  │ ──── (~ms) ──────► │ REPLICA  │ ──── (~ms) ──────► │ REPLICA  │
│  (AZ-1) │                    │  (AZ-2)  │                    │  (AZ-3)  │
└─────────┘                    └─────────┘                    └─────────┘
     ▲                              ▲
     │                              │
Strong consistent              Eventually consistent
reads go HERE                  reads can hit ANY node
```

| Mode | Behavior | Cost |
|------|----------|------|
| **Eventually Consistent** (default) | Might return stale data (~200ms lag) | **0.5 RCU** per 4 KB |
| **Strongly Consistent** (opt-in per request) | Always returns latest write | **1 RCU** per 4 KB |

> **Strongly consistent reads are NOT available on GSIs** — base table only.

---

## Conditional Writes — Optimistic Concurrency

DynamoDB supports condition expressions on writes:

```python
# Prevent overselling
UpdateItem(
    PK="PRODUCT#xyz", SK="STOCK",
    SET stock = stock - 1,
    ConditionExpression="stock > 0"
)
# If condition fails → ConditionalCheckFailedException → nothing happens

# Insert-only (prevent overwrites)
PutItem(
    PK="USER#alice", SK="ORDER#123",
    ConditionExpression="attribute_not_exists(PK)"
)

# Optimistic locking
UpdateItem(
    SET data = :new_data, version = version + 1,
    ConditionExpression="version = :expected_version"
)
```

### Conditional Expression Patterns

| Pattern | Expression | Use Case |
|---------|-----------|----------|
| Insert-only | `attribute_not_exists(PK)` | Prevent accidental overwrites |
| Exists check | `attribute_exists(status)` | Only update if attribute present |
| Value check | `balance >= :amount` | Business rule enforcement |
| Optimistic lock | `version = :expected` | Concurrent update safety |

---

## Batch & Parallel Operations

| Operation | Limit | Key Behavior |
|-----------|-------|-------------|
| `BatchGetItem` | **100 items** across multiple tables | No ordering guarantee. Each read independent. |
| `BatchWriteItem` | **25 items** (Put or Delete only) | **NO UpdateItem. NO conditions. NOT atomic — partial failures possible.** |

> **Critical:** `BatchWriteItem` can partially fail. Always check `UnprocessedItems` in response and retry.

### Return Values

`PutItem`, `UpdateItem`, `DeleteItem` can return the old/new item via `ReturnValues` parameter — avoids a separate `GetItem` call.

---

## ⚠️ Gotchas & Edge Cases

1. **`PutItem` silently overwrites** without `ConditionExpression = "attribute_not_exists(PK)"` — the #1 DynamoDB production bug
2. **Filter expressions don't save money** — you pay RCU for all data read, filter just reduces response size
3. **`Query` is ALWAYS scoped to one partition** — cannot query across PK values without a GSI
4. **`BatchWriteItem` cannot do `UpdateItem`** — only Put and Delete
5. **Strongly consistent reads NOT available on GSIs** — base table only

---

## 📌 Interview Cheat Sheet

- **Query = one partition, fast, cheap. Scan = full table, slow, expensive.** If core access patterns need Scans, your data model is wrong.
- **Filters are cosmetic** — applied after read, still consume full RCU
- **Eventually consistent = 0.5 RCU/4KB. Strongly consistent = 1 RCU/4KB.** Strong = base table only.
- **Conditional writes** = optimistic locking. Know `attribute_not_exists`, `attribute_exists`, comparison operators cold.
- **PutItem replaces. UpdateItem merges.** Never mix them up.
- **BatchWriteItem ≠ transaction.** Partial failures possible — always check `UnprocessedItems`.
- **Atomic counters:** `UpdateItem SET counter = counter + 1` — no locking needed, atomicity built-in.
