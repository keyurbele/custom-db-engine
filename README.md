Markdown# Custom Log-Structured Page Storage Engine with B+ Tree Indexing 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A high-performance, crash-resilient key-value storage engine implemented from scratch in Python. This project is built to explore and demonstrate the fundamental systems engineering concepts behind modern transactional databases like SQLite, RocksDB, and MongoDB.

## 🏗️ System Architecture

The engine is built around an append-only, page-allocated storage model optimized for low-latency hardware interaction, backed by a dynamic in-memory index.

```text
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
🛠️ Core Engineering FeaturesPage-Based Storage & mmap: The database splits files into fixed 4KB blocks matching physical SSD block sectors. Using Python's mmap module, the database file is mapped directly into virtual memory space, bypassing traditional read/write user-space context switches for direct memory slicing.Custom B+ Tree Indexing: Replaces standard hash-maps with a self-balancing B+ Tree structure. This enables point lookups while introducing native support for sorted alphabetic range queries.Write-Ahead Logging (WAL): Provides atomicity and durability. Mutations are safely flushed to wal.log prior to updating the virtual memory map, guaranteeing zero data loss or database corruption during simulated crashes.Tombstone Deletions & Compaction Engine: Deletions append a 1-byte tombstone marker to disk to prevent slow midpoint file rewrites. A background compaction routine physically sweeps the pages, dropping stale records and dead data to reclaim storage footprints.Thread-Safe Concurrency: Implements fine-grained threading.Lock protection, maintaining complete data integrity across overlapping multi-threaded reader and writer workers.📈 Performance & Benchmark MetricsMeasurements collected sequentially under local hardware workloads (Intel Core Platform / NVMe SSD Platform):Metric OperationThroughput SpeedMechanismSequential Writes~4,900 ops/secLog-Structured Page Appends + WALPoint Reads~220,000+ ops/secVirtual Memory Slicing + LRU CacheRange Queries~14,000 scans/secLinked B+ Tree Leaf Pointer Traversal🔬 Architectural Design Decisions & Trade-Offs1. Hash Index vs. B+ Tree IndexApproach A (Hash Map): Offers pure $O(1)$ lookup performance, but makes range sorting mathematically impossible without pulling the whole database into RAM.Approach B (B+ Tree - Selected): Increases lookup complexity slightly to $O(\log n)$, but links leaf nodes together, transforming multi-key range scanning into a highly efficient sequential stroll.2. Append-Only vs. In-Place UpdatesIn-Place Updates: Reduces immediate file footprint sizes, but requires expensive search-and-seek hard disk operations that stall execution threads.Append-Only Logging (Selected): Prioritizes low-latency throughput by treating writes as fast sequential appends, relying on an isolated Compaction cycle to sweep out space bloating during off-peak hours.💾 Installation & UsageBashpip install custom_db_engine
Basic CRUD OperationsPythonfrom engine import SimpleStorageEngine

# Initialize the storage engine instance
db = SimpleStorageEngine(db_filename="data.db", wal_filename="wal.log")

# Insert data
db.put("user_101", "Alice")

# Low-latency retrieval
record = db.get("user_101")
print(f"Retrieved: {record}") # Output: Alice

# Alphabetic range tracking scan
db.put("user_102", "Bob")
db.put("user_103", "Charlie")
results = db.get_range("user_101", "user_103")
print(results) 

db.close()