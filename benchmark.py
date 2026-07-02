import time
from engine import SimpleStorageEngine

def run_benchmark():
    # Initialize engine with a standard production cache size
    db = SimpleStorageEngine(db_filename="bench.db", wal_filename="bench_wal.log", cache_capacity=1000)
    
    total_records = 5000
    print(f"🚀 Starting benchmark with {total_records} operations...")
    
    # 1. Benchmark Writes (PUT)
    start_time = time.time()
    for i in range(total_records):
        db.put(f"key_{i}", f"value_data_payload_{i}")
    write_time = time.time() - start_time
    writes_per_sec = total_records / write_time
    
    # 2. Benchmark Reads (GET)
    start_time = time.time()
    for i in range(total_records):
        db.get(f"key_{i}")
    read_time = time.time() - start_time
    reads_per_sec = total_records / read_time
    
    print("\n📊 --- BENCHMARK RESULTS ---")
    print(f"✍️ Writes: {total_records} ops in {write_time:.2f}s ({writes_per_sec:.2f} ops/sec)")
    print(f"📖 Reads (Cache-Driven): {total_records} ops in {read_time:.2f}s ({reads_per_sec:.2f} ops/sec)")
    
    db.close()
    
    # Clean up benchmark files
    import os
    if os.path.exists("bench.db"): os.remove("bench.db")
    if os.path.exists("bench_wal.log"): os.remove("bench_wal.log")

if __name__ == "__main__":
    run_benchmark()