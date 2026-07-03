# Custom Log-Structured Page Storage Engine with B+ Tree Indexing

A high-performance, crash-resilient key-value storage engine implemented from scratch in Python. This project is built to explore and demonstrate the fundamental systems engineering concepts behind modern transactional databases like SQLite, RocksDB, and MongoDB.

## 🏗️ System Architecture

The engine is built around an append-only, page-allocated storage model optimized for low-latency hardware interaction, backed by a dynamic in-memory index.

              ┌────────────────────────┐
              │   Client Application   │
              └───────────┬────────────┘
                          │  put() / get() / get_range()
                          ▼
              ┌────────────────────────┐
              │ Concurrency Lock Layer │  <-- Thread-safe multi-user protection
              └───────────┬────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌─────────────────────┐             ┌─────────────────────┐
│  LRU Memory Cache   │             │   Write-Ahead Log   │
│   (Fast RAM Hits)   │             │  (wal.log Durability)│
└──────────┬──────────┘             └──────────┬──────────┘
│                                   │
│ Cache Miss                        │ Write-Ahead Protocol
▼                                   ▼
┌─────────────────────┐             ┌─────────────────────┐
│ Custom B+ Tree Map  │────────────>│ Memory-Mapped Pages │
│ (Sorted RAM Index)  │             │   (4KB data.db)     │
└─────────────────────┘             └─────────────────────┘


### 🛠️ Core Engineering Features

* **Page-Based Storage & `mmap`:** The database splits files into fixed 4KB blocks matching physical SSD block sectors. Using Python's `mmap` module, the database file is mapped directly into virtual memory space, bypassing traditional read/write user-space context switches for direct memory slicing.
* **Custom B+ Tree Indexing:** Replaces standard hash-maps with a self-balancing B+ Tree structure. This enables point lookups while introducing native support for sorted **alphabetic range queries**.
* **Write-Ahead Logging (WAL):** Provides atomicity and durability. Mutations are safely flushed to `wal.log` prior to updating the virtual memory map, guaranteeing zero data loss or database corruption during simulated crashes.
* **Tombstone Deletions & Compaction Engine:** Deletions append a 1-byte tombstone marker to disk to prevent slow midpoint file rewrites. A background compaction routine physically sweeps the pages, dropping stale records and dead data to reclaim storage footprints.
* **Thread-Safe Concurrency:** Implements fine-grained `threading.Lock` protection, maintaining complete data integrity across overlapping multi-threaded reader and writer workers.

---

## 📈 Performance & Benchmark Metrics

Stress-tested across 10,000 sequential operations, the engine achieves production-grade execution efficiency under memory-mapped configurations:

| Metric Operation | Throughput Speed | Mechanism |
| :--- | :--- | :--- |
| **Sequential Writes** | ~2,300+ ops/sec | Log-Structured Page Appends + WAL |
| **Point Reads** | **~220,000+ ops/sec** | Virtual Memory Slicing + LRU Cache |
| **Range Queries** | ~4,500+ scans/sec | Linked B+ Tree Leaf Pointer Traversal |

---

## 🔬 Architectural Design Decisions & Trade-Offs

### 1. Hash Index vs. B+ Tree Index
* *Approach A (Hash Map):* Offers pure $O(1)$ lookup performance, but makes range sorting mathematically impossible without pulling the whole database into RAM.
* *Approach B (B+ Tree - Selected):* Increases lookup complexity slightly to $O(\log n)$, but links leaf nodes together, transforming multi-key range scanning into a highly efficient sequential stroll.

### 2. Append-Only vs. In-Place Updates
* *In-Place Updates:* Reduces immediate file footprint sizes, but requires expensive search-and-seek hard disk operations that stall execution threads.
* *Append-Only Logging (Selected):* Prioritizes low-latency throughput by treating writes as fast sequential appends, relying on an isolated Compaction cycle to sweep out space bloating during off-peak hours.

---

## 🚀 CI/CD Cloud Automation

The engine includes a complete **GitHub Actions** pipeline configured via `.github/workflows/tests.yml`. Every single update pushed to the remote repository instantly provisions a clean `ubuntu-latest` container running Python 3.12, verifying all page structures, memory maps, crash recoveries, and tree boundary constraints automatically.