# EC2 Storage, Networking & Placement Groups

## Storage — EBS vs Instance Store

| | **EBS** | **Instance Store** |
|--|---------|-------------------|
| **Analogy** | USB drive plugged in | HDD soldered on motherboard |
| **Persistence** | ✅ Survives stop/restart | ❌ GONE on stop/terminate |
| **Attachment** | Network-attached | Physically local NVMe |
| **Latency** | Sub-ms (Nitro) | Lower, higher throughput |
| **Snapshots** | ✅ Incremental → S3 | ❌ None |
| **Max Size** | 64 TiB per volume | Fixed by instance type |
| **Scope** | **AZ-locked** | Tied to instance lifecycle |
| **Use Case** | Boot volumes, DBs | Scratch, caches, shuffle |

---

## EBS Volume Types

| Type | IOPS | Throughput | Best For |
|------|------|-----------|----------|
| **gp3** ⭐ | 3K base → 16K | 125 → 1,000 MiB/s | **Default for everything** |
| **gp2** (legacy) | Burst 3K, 3/GB | 250 MiB/s | Avoid — prefer gp3 |
| **io2 Block Express** | Up to **256K** | 4,000 MiB/s | Guaranteed IOPS (Oracle, SAP) |
| **st1** | 500 | 500 MiB/s | Big data, logs (sequential) |
| **sc1** | 250 | 250 MiB/s | Archive, lowest cost |

### EBS Volume Type Selection

```mermaid
flowchart TD
    START{"What's your\nworkload?"}
    START -->|"General purpose\n(most workloads)"| GP3["✅ gp3\n3K IOPS baseline\nscale independently"]
    START -->|"Need guaranteed\nhigh IOPS"| IO2["✅ io2 Block Express\nup to 256K IOPS"]
    START -->|"Sequential reads\n(big data, logs)"| ST1["✅ st1\nThroughput HDD"]
    START -->|"Archive /\nlowest cost"| SC1["✅ sc1\nCold HDD"]

    style GP3 fill:#2d6a4f,color:#fff
    style IO2 fill:#6a0572,color:#fff
    style ST1 fill:#1a535c,color:#fff
    style SC1 fill:#6c757d,color:#fff
```

> **[SDE2 TRAP]** gp2 IOPS scales with size (3/GB). 100 GB gp2 = only 300 IOPS. **gp3 decouples IOPS from size** — always 3,000 baseline. Always recommend gp3.

### EBS Key Behaviors

| Behavior | Detail |
|----------|--------|
| **AZ-locked** | Volume in `1a` can't attach to instance in `1b`. Migrate via snapshot. |
| **Snapshots** | Incremental. Deleting old snaps is safe — AWS redistributes blocks. |
| **Multi-Attach** | io2 only. NOT a shared FS — needs cluster-aware FS (GFS2) or corruption. |
| **Encryption** | AES-256 via KMS. Transparent. Encrypt at creation or during snap copy. |
| **EBS-optimized** | Nitro instances (m5+) are EBS-optimized by default, no extra cost. |

### EBS Cross-AZ / Cross-Region Migration

```mermaid
flowchart LR
    VOL["EBS Volume\nus-east-1a"] -->|"snapshot"| SNAP["EBS Snapshot\n(stored in S3)"]
    SNAP -->|"restore in\nnew AZ"| VOL2["New Volume\nus-east-1b"]
    SNAP -->|"copy cross-region"| SNAP2["Snapshot Copy\neu-west-1"]
    SNAP2 -->|"restore"| VOL3["New Volume\neu-west-1a"]

    style SNAP fill:#ff9f1c,color:#000
    style VOL2 fill:#2d6a4f,color:#fff
    style VOL3 fill:#6a0572,color:#fff
```

---

## ENI (Elastic Network Interface)

Virtual network card. Every instance has at least one.

**An ENI carries:** Private IP + Public/Elastic IP + Security Groups + MAC address

### Why ENIs Matter

| Use Case | How |
|----------|-----|
| **Failover without IP change** | Detach ENI from failed instance → attach to standby → same IP, zero DNS delay |
| **Multi-homed instances** | ENI-1 in public subnet (web), ENI-2 in private subnet (DB access) |
| **License preservation** | Software bound to MAC → ENI preserves MAC across instance replacements |

### ENI Failover Pattern

```mermaid
flowchart LR
    subgraph BEFORE["Before Failure"]
        A1["Instance A\n(primary)"] --- ENI1["ENI\n10.0.1.50\nSG: web-sg"]
        B1["Instance B\n(standby)"]
    end

    subgraph AFTER["After Failure"]
        A2["Instance A ❌\n(failed)"]
        B2["Instance B\n(promoted)"] --- ENI2["ENI\n10.0.1.50\nSame IP ✅"]
    end

    BEFORE -->|"detach + reattach"| AFTER

    style A2 fill:#dc3545,color:#fff
    style ENI2 fill:#2d6a4f,color:#fff
```

> **[SDE2 TRAP]** Security Groups attach to **ENIs**, not instances. Two ENIs on one instance can have different SGs. Common debugging pitfall.

---

## Placement Groups

| Strategy | Behavior | Limit | Use Case | Risk |
|----------|----------|-------|----------|------|
| **Cluster** | Same rack, low-latency interconnect | No limit | HPC, MPI, 10 Gbps inter-node | Rack failure = all down |
| **Spread** | Each on different hardware | **7 per AZ** | Critical instances — no shared fate | Limited count |
| **Partition** | Grouped partitions on separate racks | 7 partitions/AZ | Cassandra, Kafka, HDFS | Less granular |

### Placement Group Decision

```mermaid
flowchart TD
    Q{"What matters most?"}
    Q -->|"Lowest latency\nbetween instances"| CLUSTER["Cluster\n• Same rack\n• 10 Gbps interconnect\n• HPC, MPI"]
    Q -->|"Maximum fault\nisolation"| SPREAD["Spread\n• Different hardware\n• Max 7 per AZ\n• Critical instances"]
    Q -->|"Large distributed\nsystem"| PARTITION["Partition\n• Rack-aware groups\n• 7 partitions/AZ\n• Cassandra, Kafka, HDFS"]

    style CLUSTER fill:#ff9f1c,color:#000
    style SPREAD fill:#2d6a4f,color:#fff
    style PARTITION fill:#6a0572,color:#fff
```

---

## Interview Cheat Sheet

- EBS = persistent, network-attached, AZ-scoped. Instance Store = ephemeral, local, blazing fast.
- gp3 > gp2 (decoupled IOPS). io2 for guaranteed IOPS. st1/sc1 for sequential/cold.
- EBS snapshots are incremental, stored in S3, cross-region copyable.
- EBS Multi-Attach ≠ shared filesystem. Needs cluster-aware FS.
- ENI = virtual NIC (IP + SG + MAC). Movable for failover. SGs attach to ENIs, not instances.
- Placement Groups: Cluster (performance), Spread (resilience, 7/AZ), Partition (distributed DBs).
