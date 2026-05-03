# AWS DynamoDB — Single-Table Design & Advanced Query Patterns

## Why Single-Table Design?

In RDBMS: normalize into separate tables, JOIN at read time.
In DynamoDB: **JOINs don't exist.** Every Query hits one table, one partition.

**Two approaches:**

| Approach | Pros | Cons |
|----------|------|------|
| **Multi-table** | Simple to understand, clear entity boundaries | Multiple API calls, harder consistency, more network round trips |
| **Single-table** | Fetch related entities in ONE Query, fewer round trips, lower latency | Higher design complexity, harder to evolve |

> AWS recommends single-table for high-performance apps. Interviewers expect you to know it.

---

## The Core Principle: Access-Pattern-First Design

```
Step 1: List EVERY access pattern your app needs.
        Not "what data do I have?" but "what questions will I ask?"

Step 2: Design PK + SK so each pattern maps to a single Query or GetItem.

Step 3: Add GSIs ONLY for patterns the base table can't serve.
```

> **The rule:** PK = "who's asking?" SK = "what are they asking for?"

---

## Overloaded Keys — The Foundation

PK and SK hold **different entity types**, distinguished by prefixes:

```
PK                    SK                      Attributes
─────────────────────────────────────────────────────────────
USER#alice            PROFILE                 {name: "Alice", email: "a@x.com"}
USER#alice            ORDER#2024-01-15        {total: 59.99, status: "shipped"}
USER#alice            ORDER#2024-03-22        {total: 120.00, status: "pending"}
USER#alice            REVIEW#prod_42          {stars: 5, text: "Great product"}
PRODUCT#prod_42       METADATA                {name: "Widget", price: 29.99}
PRODUCT#prod_42       REVIEW#alice            {stars: 5, text: "Great product"}
```

### Access Patterns Served

| Access Pattern | Query |
|---|---|
| Alice's profile | `GetItem(PK=USER#alice, SK=PROFILE)` |
| All of Alice's orders | `Query(PK=USER#alice, SK begins_with ORDER#)` |
| Alice's latest order | `Query(PK=USER#alice, SK begins_with ORDER#, ScanIndexForward=false, Limit=1)` |
| Product metadata | `GetItem(PK=PRODUCT#prod_42, SK=METADATA)` |
| All reviews for a product | `Query(PK=PRODUCT#prod_42, SK begins_with REVIEW#)` |

**One table. Five access patterns. Zero Scans. Zero JOINs.**

---

## The Adjacency List Pattern (Many-to-Many)

For relationships like users ↔ groups, students ↔ courses:

```
PK                  SK                    Data
──────────────────────────────────────────────────
USER#alice          GROUP#engineering     {joined: "2024-01-01"}
USER#alice          GROUP#book-club       {joined: "2024-06-15"}
GROUP#engineering   USER#alice            {role: "lead"}
GROUP#engineering   USER#bob              {role: "member"}
```

| Pattern | Query |
|---|---|
| All groups Alice is in | `Query(PK=USER#alice, SK begins_with GROUP#)` |
| All members of Engineering | `Query(PK=GROUP#engineering, SK begins_with USER#)` |

**Alternative:** Store one direction only + GSI with inverted keys (GSI PK=SK, GSI SK=PK) for reverse lookup. Avoids duplication at cost of eventual consistency on reverse.

---

## GSI Overloading

A single GSI serves **multiple entity types** by overloading the key attributes:

```
GSI1-PK             GSI1-SK              Entity
──────────────────────────────────────────────────
shipped             2024-01-15           ORDER
pending             2024-03-22           ORDER
admin               USER#alice           USER
```

One GSI answers both "all shipped orders by date" AND "all admin users."

---

## Advanced Sort Key Patterns

### Composite Sort Keys — Hierarchical Filtering

Pack multiple dimensions into SK:

```
SK = STATUS#shipped#DATE#2024-01-15#REGION#us-east-1
```

Queryable paths (left-to-right only):
- `begins_with("STATUS#shipped")` → all shipped
- `begins_with("STATUS#shipped#DATE#2024-01")` → shipped in Jan 2024
- `begins_with("STATUS#shipped#DATE#2024-01-15#REGION#us")` → shipped Jan 15 in US

> **[SDE2 TRAP]** You CANNOT skip levels. Can't query "all shipped in us-east regardless of date." The left-to-right hierarchy order of your composite key must match your most common drill-down path.

### Sparse Indexes

GSI on an attribute only some items have → items without that attribute are **excluded from the index.** Natural filtering, zero cost.

### Zero-Padding for Lexicographic Sort

DynamoDB sorts strings lexicographically, not numerically:

```
BAD:   "ORDER#9", "ORDER#10"    → sorted as: 10, 9 (WRONG — "9" > "1")
GOOD:  "ORDER#0009", "ORDER#0010" → sorted as: 0009, 0010 (correct)
```

---

## Real-World Example: Social Media App

```
PK                  SK                          Attributes
──────────────────────────────────────────────────────────────────
USER#alice          PROFILE                     {bio, avatar, joined}
USER#alice          POST#2024-05-01T10:00       {text: "Hello world", likes: 42}
USER#alice          POST#2024-05-02T14:30       {text: "DynamoDB rocks", likes: 7}
USER#alice          FOLLOWER#bob                {since: "2024-01-01"}
POST#alice#05-01    LIKE#bob                    {at: "2024-05-01T10:05"}
POST#alice#05-01    LIKE#charlie                {at: "2024-05-01T10:12"}
```

- Alice's recent posts → `Query(PK=USER#alice, SK begins_with POST#, Reverse, Limit 10)`
- Alice's followers → `Query(PK=USER#alice, SK begins_with FOLLOWER#)`
- "Does Bob follow Alice?" → `GetItem(PK=USER#alice, SK=FOLLOWER#bob)` — O(1) lookup
- GSI (inverted keys) → "Who does Bob follow?" → `Query(GSI PK=FOLLOWER#bob)`

---

## ⚠️ Gotchas & Edge Cases

1. **Data duplication is expected.** Review appears under both USER and PRODUCT. Update means updating multiple items — this is the accepted tradeoff.
2. **Composite SK order is irreversible.** `STATUS#DATE#REGION` ≠ `STATUS#REGION#DATE`. Map most common drill-down to left-to-right order.
3. **Don't force single-table.** Completely unrelated entities with no co-access → separate tables are simpler and fine.
4. **Item collection size with LSIs.** All items sharing a PK cannot exceed 10 GB combined.
5. **"All items of type X" across partitions requires a GSI.** Base table only queries within one PK.
6. **Schema evolution is harder.** Adding a new entity type to a single-table design requires careful key design to avoid conflicts.

---

## 📌 Interview Cheat Sheet

- **Start with access patterns, NOT entities.** List every query first.
- **PK = "who's asking?" SK = "what are they asking for?"**
- **Overloaded keys:** PK/SK use prefixes (`USER#`, `ORDER#`) to mix entity types
- **Adjacency list** = many-to-many. Store both directions OR inverted GSI.
- **Composite SK** = hierarchical filter, left-to-right only. Key segment order = query drill-down priority.
- **Sparse index** = GSI on optional attribute → auto-filtered index
- **GSI overloading** = multiple entity types reuse same GSI with different semantic key values
- **Data duplication is a feature** — trade storage for query performance
- When interviewer asks "how do you model X?" → start with **access patterns**, then key design. Entity-first = RDBMS mindset = red flag.
