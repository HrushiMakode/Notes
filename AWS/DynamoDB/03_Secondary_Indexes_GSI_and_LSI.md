# AWS DynamoDB — Secondary Indexes (GSI & LSI)

## The Problem Indexes Solve

Your base table key serves **one access pattern.** Real apps need many:

```
Table: Orders (PK = user_id, SK = order_date)

✅ "Get all orders for user Alice"           → Query PK = alice
✅ "Get Alice's orders from March 2024"      → Query PK = alice, SK begins_with "2024-03"
❌ "Get all orders with status = shipped"    → Can't query by status — not a key
❌ "Get all orders by product_id"            → product_id isn't a key either
```

Without indexes → full `Scan` with filter. Indexes create **alternate key structures** over the same data.

---

## GSI vs LSI — Side by Side

| Feature | LSI (Local Secondary Index) | GSI (Global Secondary Index) |
|---|---|---|
| **Partition Key** | **Same** as base table | **Different** — completely new |
| **Sort Key** | Different from base table | Optional, can be different |
| **When to create** | **Table creation only** — cannot add later | **Anytime** |
| **Limit** | 5 per table | 20 per table (soft limit) |
| **Consistency** | Supports **strong consistency** | **Eventually consistent ONLY** |
| **Storage** | Co-located with base table partition | Separate partition space |
| **Throughput** | Shares base table capacity | **Separate RCU/WCU** |
| **Size constraint** | **10 GB per partition key** (all items with same PK) | No limit |

### Mental Model

```
BASE TABLE (PK = user_id, SK = order_date)
├── Partition: user_id = "alice"
│   ├── order_date = "2024-01-15" → {status: "shipped",  product: "book"}
│   └── order_date = "2024-03-22" → {status: "pending",  product: "pen"}

                    │
          ┌─────────┴──────────┐
          ▼                    ▼

LSI (PK = user_id, SK = status)       GSI (PK = status, SK = order_date)
├── alice                              ├── "shipped"
│   ├── "pending" → ...                │   ├── "2024-01-15" → alice, book
│   └── "shipped" → ...                │   └── "2024-02-10" → bob, laptop
                                       ├── "pending"
SAME partitions,                       │   └── "2024-03-22" → alice, pen
different sort order
                                       DIFFERENT partitions,
                                       re-partitioned by status
```

---

## Projections — What Gets Copied to the Index

| Projection Type | What's Copied | Tradeoff |
|---|---|---|
| `KEYS_ONLY` | Base PK + SK + index keys | Min storage, but need follow-up `GetItem` for other attributes |
| `INCLUDE` | Keys + specific named attributes | Middle ground |
| `ALL` | Every attribute from base table | Max storage + write cost, but no follow-up reads |

> **[SDE2 TRAP]** GSI projections are **immutable after creation.** Wrong projection choice = delete GSI and recreate it. Choose wisely.

> **[SDE2 TRAP]** GSI storage is NOT free. `ALL` projection on 100 GB table ≈ another 100 GB. Every base table write also writes to every GSI = **write amplification**.

---

## Key Patterns

### Inverted Index Pattern

GSI with PK and SK swapped from base table:

```
Base Table: PK = TENANT#acme,  SK = USER#alice
GSI:        PK = USER#alice,   SK = TENANT#acme

Base: "All users in tenant Acme"   → Query base PK = TENANT#acme
GSI:  "All tenants Alice belongs to" → Query GSI PK = USER#alice
```

### Sparse Index Pattern

GSI on an attribute that only some items have:

```
Only flagged orders have a `flagged_at` attribute.
GSI: PK = flagged_at → Only flagged orders appear in this GSI.
```

No filter needed. The GSI naturally excludes non-flagged items. Free, efficient filtering.

---

## ⚠️ Gotchas & Edge Cases

1. **GSIs are eventually consistent ONLY.** Write → immediately query GSI → might not see the item. For read-after-write, query the base table.
2. **LSIs cannot be added after table creation.** Permanent decision. When unsure, lean toward GSIs.
3. **GSI throttling back-pressures the base table.** If GSI write capacity is exhausted, base table writes get throttled too.
4. **LSI imposes a 10 GB partition limit.** All items with same PK (base + LSI data) cannot exceed 10 GB.
5. **Cannot Query a GSI with strong consistency.** Workaround: fetch keys from GSI → `BatchGetItem` with `ConsistentRead=True` on base table.
6. **Sparse indexes:** items missing the GSI key attribute are excluded from the index — powerful for filtered indexes.

---

## 📌 Interview Cheat Sheet

- **GSI = new PK+SK, added anytime, eventually consistent only, separate throughput**
- **LSI = same PK, different SK, table creation only, supports strong consistency, 10 GB limit**
- GSI writes are **asynchronous** — write amplification (every base write → N GSI writes)
- **Sparse index:** items missing GSI key attribute are auto-excluded
- **Inverted index:** GSI where PK and SK swapped from base table
- **Projections are immutable.** Cannot change after creation — must delete + recreate GSI.
- "Why not add more GSIs?" → write amplification, storage cost, GSI throttling back-pressure
- `KEYS_ONLY` → min storage, extra reads. `ALL` → max storage, no extra reads. Choose based on access frequency.
