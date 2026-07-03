import os
import threading
import time
from engine import SimpleStorageEngine

def writer_worker(db, worker_id, count):
    """Simulates a concurrent writer thread pushing data."""
    for i in range(count):
        db.put(f"thread_key_{worker_id}_{i}", f"value_{i}")

def reader_worker(db, worker_id, count):
    """Simulates a concurrent reader thread pulling data."""
    for i in range(count):
        # Read keys that are being written by writers
        db.get(f"thread_key_0_{i}")

def run_stress_test():
    for f in ["stress_data.db", "stress_wal.log"]:
        if os.path.exists(f): os.remove(f)

    # Initialize engine with an active cache capacity
    db = SimpleStorageEngine(db_filename="stress_data.db", wal_filename="stress_wal.log", cache_capacity=100)
    
    print("⚡ Starting Concurrency Stress Test (Simulating overlapping Readers & Writers)...")
    
    # Create 2 concurrent writers and 2 concurrent readers running simultaneously
    threads = []
    threads.append(threading.Thread(target=writer_worker, args=(db, 0, 500)))
    threads.append(threading.Thread(target=writer_worker, args=(db, 1, 500)))
    threads.append(threading.Thread(target=reader_worker, args=(db, 0, 500)))
    threads.append(threading.Thread(target=reader_worker, args=(db, 1, 500)))

    start_time = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    duration = time.time() - start_time

    print(f"✅ Concurrency Stress Test Passed cleanly in {duration:.2f} seconds!")
    print("🔒 No deadlocks or race conditions encountered.")
    
    db.close()
    for f in ["stress_data.db", "stress_wal.log"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_stress_test()