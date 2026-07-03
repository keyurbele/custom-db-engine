import os
import time
from engine import SimpleStorageEngine

def run_benchmarks():
    # Clear out previous artifacts
    for f in ["bench_data.db", "bench_wal.log"]:
        if os.path.exists(f): os.remove(f)

    # High capacity to stress memory mapping throughput
    db = SimpleStorageEngine(db_filename="bench_data.db", wal_filename="bench_wal.log", cache_capacity=5000)
    
    total_ops = 10000
    print(f"🚀 Launching Stress Tests ({total_ops} operations via mmap)...")

    # 1. Benchmark Sequential Writes
    start_time = time.time()
    for i in range(total_ops):
        db.put(f"key_{i}", f"value_{i}")
    write_duration = time.time() - start_time
    write_ops_sec = total_ops / write_duration

    # 2. Benchmark Cache-Driven Reads
    start_time = time.time()
    for i in range(total_ops):
        db.get(f"key_{i}")
    read_duration = time.time() - start_time
    read_ops_sec = total_ops / read_duration

    print("\n--- 📈 PHASE 8 BENCHMARK METRICS ---")
    print(f"✨ Mapped Writes: {total_ops} ops in {write_duration:.2f}s ({write_ops_sec:.2f} ops/sec)")
    print(f"✨ Mapped Reads : {total_ops} ops in {read_duration:.2f}s ({read_ops_sec:.2f} ops/sec)")
    print(f"📦 Total Allocated DB Storage Size: {db.db_size} bytes")
    
    db.close()
    
    # Clean up bench files
    for f in ["bench_data.db", "bench_wal.log"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_benchmarks()