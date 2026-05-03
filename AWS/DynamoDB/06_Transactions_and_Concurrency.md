# AWS DynamoDB — Transactions & Concurrency

## The Problem: Multi-Item Atomicity

Without transactions, DynamoDB operations are atomic at the **single-item level only.** If business logic needs to update 3 items together and the process crashes midway — inconsistent data.

---

## TransactWriteItems

Groups up to **100 actions** into a single all-or-nothing operation:

| Action | What It Does |
|--------|-------------|
| `Put` | Create/replace an item |
| `Update` | Modify specific attributes |
| `Delete` | Remove an item |
| `ConditionCheck` | Assert a condition **without modifying** the item |

```python
TransactWriteItems([
    # Debit alice (only if sufficient balance)
    Update(PK="ACCOUNT#alice", SK="BALANCE",
        SET balance = balance - 50,
        Condition="balance >= 50"),

    # Credit bob
    Update(PK="ACCOUNT#bob", SK="BALANCE",
        SET balance = balance + 50),

    # Idempotency guard (only if this TX doesn't already exist)
    Put(PK="TX#uuid-123", SK="METADATA",
        {amount: 50, from: "alice", to: "bob"},
        Condition="attribute_not_exists(PK)")
])
# Either ALL three succeed or NONE do.
```

## TransactGetItems

Reads up to **100 items** with **serializable isolation** — all items read at a consistent point in time:

```python
TransactGetItems([
    Get(PK="ACCOUNT#alice", SK="BALANCE"),
    Get(PK="ACCOUNT#bob", SK="BALANCE"),
])
# Both reads reflect the EXACT same moment — unlike BatchGetItem
```

---

## ACID in DynamoDB

| Property | Guarantee |
|----------|-----------|
| **Atomicity** | All items succeed or all fail. No partial writes. |
| **Consistency** | Condition expressions evaluated atomically. Any failure → full rollback. |
| **Isolation** | **Serializable** — strongest level. Concurrent transactions on same items are serialized. |
| **Durability** | Success = persisted across 3 AZs. |

> **[SDE2 TRAP]** DynamoDB transactions provide **serializable isolation** — STRONGER than most RDBMS defaults (typically read-committed). Know this for interviews.

---

## Concurrency Control Hierarchy

**Always pick the cheapest mechanism that solves the problem:**

| Scenario | Mechanism | Cost |
|----------|-----------|------|
| Atomic increment (counter, stock) | `UpdateItem SET x = x + 1` | **1 WCU** — built-in atomicity, no locks |
| Prevent overwrites | `PutItem` + `attribute_not_exists(PK)` | **1 WCU** |
| Single-item read-modify-write | **Optimistic locking** (version attribute) | **1 WCU** + retry logic |
| Multi-item atomicity | `TransactWriteItems` | **2 WCU per item** |

### Optimistic Locking Pattern

```python
# Read the item
item = GetItem(PK="PRODUCT#42")  # item.version = 3

# Update with version check
UpdateItem(
    PK="PRODUCT#42",
    SET stock = stock - 1, version = version + 1,
    ConditionExpression="version = :v",
    ExpressionAttributeValues={":v": 3}
)
# If another process already changed version → ConditionalCheckFailedException → retry
```

### The Lost Update Bug (Classic Interview Scenario)

```
Lambda A: Read item (counter=10) → increment in memory → PutItem(counter=11)
Lambda B: Read item (counter=10) → increment in memory → PutItem(counter=11)

Result: counter = 11 (should be 12). One update LOST.

Fix 1: UpdateItem SET counter = counter + 1 (atomic, simplest)
Fix 2: Optimistic locking with version attribute
Fix 3: TransactWriteItems (overkill for single item)
```

---

## Idempotency in Transactions

Network failures can cause your app to **miss the success response.** Retry = double execution.

### Fix 1: Manual Idempotency Item

```python
TransactWriteItems([
    Update(...debit alice...),
    Update(...credit bob...),
    Put(PK="IDEMPOTENCY#<request-id>", SK="TX",
        Condition="attribute_not_exists(PK)")  # fails if already processed
])
```

### Fix 2: Built-in ClientRequestToken

`TransactWriteItems` supports `ClientRequestToken` — deduplicates retries for **10 minutes** automatically.

---

## Real-World Example: E-Commerce Checkout

```python
TransactWriteItems([
    # 1. Decrement inventory (only if in stock)
    Update(PK="PRODUCT#widget", SK="STOCK",
        SET stock = stock - :qty,
        Condition="stock >= :qty"),

    # 2. Create order (only if doesn't exist)
    Put(PK="USER#alice", SK="ORDER#2024-05-03",
        {total: 59.99, product: "widget", qty: 2},
        Condition="attribute_not_exists(SK)"),

    # 3. Debit wallet (only if sufficient balance)
    Update(PK="USER#alice", SK="WALLET",
        SET balance = balance - :total,
        Condition="balance >= :total"),

    # 4. Idempotency guard
    Put(PK="IDEMPOTENCY#req-abc-123", SK="CHECKOUT",
        Condition="attribute_not_exists(PK)")
])
# Out of stock / insufficient balance / duplicate request → NOTHING happens.
```

---

## ⚠️ Gotchas & Edge Cases

1. **2x the cost.** Transactional reads = 2 RCU/4KB. Transactional writes = 2 WCU/1KB. Don't use when a conditional update suffices.
2. **100 items max per transaction.** Max 4 MB total request size. For bulk ops, use `BatchWriteItem` + app-level compensation.
3. **All items must be in the same region.** No cross-region transactions. Global Tables use LWW, not transactions.
4. **No two actions can target the same item.** Can't Put and Update same PK+SK in one `TransactWriteItems`.
5. **Conflicts cause cancellation, not queuing.** Two concurrent transactions on same item → one gets `TransactionCanceledException`. Your app must retry.
6. **`ConditionCheck` is an action that does nothing** but counts toward 100-item limit and costs WCU. Used to assert conditions on items you don't want to modify.

---

## 📌 Interview Cheat Sheet

- **TransactWriteItems:** up to 100 actions (Put/Update/Delete/ConditionCheck), all-or-nothing, **2x WCU cost**
- **TransactGetItems:** up to 100 reads, serializable isolation, **2x RCU cost**
- Isolation level = **serializable** — stronger than most RDBMS defaults
- **Concurrency hierarchy:** atomic counter (1 WCU) → conditional write (1 WCU) → optimistic lock (1 WCU + retry) → transaction (2 WCU). Always pick cheapest.
- **Idempotency:** `ClientRequestToken` (auto 10-min dedup) or manual idempotency item
- Cannot target **same item twice** in one transaction
- Transactions work across tables but **within one region only**
- "Does DynamoDB support ACID?" → Yes, since 2018. Serializable isolation. 2x cost. 100-item limit.
