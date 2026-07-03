import os
import time
from engine import SimpleStorageEngine

def run_benchmarks():
    for f in ["bench_data.db", "bench_wal.log"]:
        if os.path.exists(f): os.remove(f)

    db = SimpleStorageEngine(db_filename="bench_data.db", wal_filename="bench_wal.log", cache_capacity=5000)
    
    total_ops = 10000
    print(f"🚀 Launching Phase 9 B+ Tree Stress Tests ({total_ops} operations)...")

    # 1. Benchmark Writes
    start_time = time.time()
    for i in range(total_ops):
        db.put(f"key_{i:05d}", f"value_{i}")
    write_duration = time.time() - start_time
    write_ops_sec = total_ops / write_duration

    # 2. Benchmark Range Searches
    range_ops = 1000
    start_time = time.time()
    for i in range(range_ops):
        # Scan blocks of 50 items alphabetically
        db.get_range(f"key_{i:05d}", f"key_{i+50:05d}")
    range_duration = time.time() - start_time
    range_ops_sec = range_ops / range_duration

    print("\n--- 📈 PHASE 9 B+ TREE BENCHMARK METRICS ---")
    print(f"✨ Mapped Writes     : {total_ops} ops in {write_duration:.2f}s ({write_ops_sec:.2f} ops/sec)")
    print(f"✨ Tree Range Scans  : {range_ops} ops in {range_duration:.2f}s ({range_ops_sec:.2f} scans/sec)")
    
    db.close()
    for f in ["bench_data.db", "bench_wal.log"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_benchmarks()