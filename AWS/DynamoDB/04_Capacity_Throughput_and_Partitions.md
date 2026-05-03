# AWS DynamoDB — Capacity, Throughput & Partition Internals

## Two Capacity Modes

### Provisioned Mode
You specify exact reads/writes per second. Pay for what you provision, whether used or not.

- **RCU (Read Capacity Unit):** 1 RCU = 1 strongly consistent read/sec for item up to **4 KB**
- **WCU (Write Capacity Unit):** 1 WCU = 1 write/sec for item up to **1 KB**

### On-Demand Mode
No provisioning. DynamoDB handles scaling. Pay per-request (~5x more expensive at steady state).

### Decision Matrix

| Signal | Provisioned | On-Demand |
|--------|------------|-----------|
| Traffic | Predictable, steady | Spiky, unpredictable, new workloads |
| Cost priority | Need to optimize | Need to avoid outages |
| Forecast ability | Know RCU/WCU needs | No idea yet |
| Scaling speed | Auto-scaling reacts in 5-15 min | Instant (mostly) |

> **[SDE2 TRAP]** On-demand is NOT infinitely elastic. Scales based on **prior peak traffic**. New tables start at ~4,000 WCU / 12,000 RCU. Day-one launch with 50K writes/sec WILL throttle. Pre-warm with provisioned mode first.

> Switching between modes: **once every 24 hours only.**

---

## RCU / WCU Math — Interview Staple

### Read Formula

```
RCU = ⌈ item_size / 4 KB ⌉ × reads_per_second

Eventually consistent:  divide by 2   (0.5 RCU per read)
Strongly consistent:    as-is         (1 RCU per read)
Transactional read:     multiply by 2 (2 RCU per read)
```

### Write Formula

```
WCU = ⌈ item_size / 1 KB ⌉ × writes_per_second

Transactional write:    multiply by 2 (2 WCU per write)
```

### Worked Examples

**Example 1:** Read 80 items/sec, each 6 KB, eventually consistent:
```
⌈6 / 4⌉ = 2 RCU per read
2 × 80 = 160 RCU (strong)
160 / 2 = 80 RCU (eventually consistent)
```

**Example 2:** Write 50 items/sec, each 2.5 KB:
```
⌈2.5 / 1⌉ = 3 WCU per write (rounds UP)
3 × 50 = 150 WCU
```

**Example 3:** Transaction with 4 writes, each 2 KB:
```
⌈2 / 1⌉ = 2 WCU per write
Transactional: 2 × 2 = 4 WCU per item
4 items × 4 = 16 WCU total
```

### Quick Reference Card

| Operation Type | Unit Size | Cost Multiplier |
|---|---|---|
| Read (eventual) | 4 KB | **0.5 RCU** |
| Read (strong) | 4 KB | **1 RCU** |
| Read (transactional) | 4 KB | **2 RCU** |
| Write (standard) | 1 KB | **1 WCU** |
| Write (transactional) | 1 KB | **2 WCU** |

---

## Partition Internals

DynamoDB stores data in **partitions** — each is a ~10 GB SSD-backed storage unit.

### Per-Partition Limits

| Resource | Maximum |
|----------|---------|
| **Read throughput** | 3,000 RCU |
| **Write throughput** | 1,000 WCU |
| **Storage** | 10 GB |

When any limit is exceeded, DynamoDB **splits** the partition.

### How Items Land in Partitions

```
PK value → hash(PK) → maps to partition range → lands on Partition N

PK = "alice"   → hash("alice")   = 0x3A7F... → Partition 2
PK = "bob"     → hash("bob")     = 0xC1D2... → Partition 7
PK = "charlie" → hash("charlie") = 0x8E01... → Partition 5
```

### The Hot Partition Problem

```
Table: 10,000 WCU across 10 partitions = 1,000 WCU per partition

If PK = "CELEBRITY_USER" gets 5,000 WCU...
But its partition ceiling = 1,000 WCU
→ THROTTLED, even though TABLE has spare capacity
```

> **"Table has capacity but I'm throttled" = hot partition.** This is the single most common DynamoDB interview question.

### Diagnosing Hot Partitions

CloudWatch → DynamoDB → **Contributor Insights** — reveals the most-accessed PK values instantly.

### Adaptive Capacity (AWS's Mitigation)

1. **Burst capacity:** Each partition banks 300 seconds of unused throughput for short spikes.
2. **Adaptive reallocation:** DynamoDB shifts capacity from idle partitions to hot ones (within minutes).
3. **Hot key isolation (since 2019):** DynamoDB can split a partition specifically for a hot key, giving it dedicated throughput.

> Adaptive capacity helps but is **NOT a substitute** for good key design. Permanently skewed traffic (1 PK = 90% of traffic) can't be saved.

### Fixes for Hot Partitions

| Fix | How It Works |
|-----|-------------|
| **Better PK cardinality** | Use high-cardinality, well-distributed keys |
| **Write sharding** | Append random suffix: `ORDER#123#shard_0-9`. Read all 10 shards + merge. |
| **Caching (DAX/Redis)** | Absorb repeated reads before they hit DynamoDB |
| **Switch to on-demand** | More aggressive adaptive capacity |

---

## ⚠️ Gotchas & Edge Cases

1. **Auto-scaling has 5-15 min lag.** For predictable spikes (flash sales), pre-scale manually.
2. **On-demand hidden ceiling.** New tables start at ~4K WCU. Only scales based on observed traffic.
3. **Minimum charge: 1 WCU per write, 0.5 RCU per read.** A 400-byte write = 1 WCU. A 100-byte eventual read = 0.5 RCU.
4. **GSI capacity is separate.** If base table has 5K WCU but GSI only has 1K → GSI throttles AND back-pressures base table.
5. **Charged per RCU/WCU, not per item.** Reads chunked in 4 KB. Writes chunked in 1 KB. Always rounds up.

---

## 📌 Interview Cheat Sheet

- **RCU: ⌈item/4KB⌉. WCU: ⌈item/1KB⌉.** Eventual = half. Transactional = double. Never mix up 4 KB and 1 KB.
- Each partition: max **3,000 RCU + 1,000 WCU + 10 GB**
- Hot partitions = #1 production issue. High-cardinality, uniform PK distribution is the fix.
- **Adaptive capacity** helps but doesn't replace good key design
- On-demand ≈ 5x more expensive than well-tuned provisioned at steady state
- Auto-scaling: **5-15 min lag** — won't save you from instant spikes
- **"Table has WCU headroom but throttling"** → Answer: hot partition. Diagnose with Contributor Insights.
