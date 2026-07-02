import os
import struct
import threading  # NEW: Import Python's threading system
import time
from collections import OrderedDict

class SimpleStorageEngine:
    def __init__(self, db_filename="data.db", wal_filename="wal.log", cache_capacity=3):
        self.db_filename = db_filename
        self.wal_filename = wal_filename
        
        self.file = open(self.db_filename, "a+b")
        self.wal_file = open(self.wal_filename, "a+b")
        
        self.index = {}
        self.cache = OrderedDict()
        self.cache_capacity = cache_capacity
        
        # NEW: Create a Thread Lock to ensure only one thread writes to disk at a time!
        self.lock = threading.Lock()
        
        self._recover_from_wal()
        self._load_index()

    def _recover_from_wal(self):
        """Scans the WAL file on startup for automatic crash recovery."""
        self.wal_file.seek(0, os.SEEK_END)
        wal_size = self.wal_file.tell()
        if wal_size == 0:
            return
            
        print("⚠️ Database did not close cleanly! Starting Crash Recovery via WAL...")
        self.wal_file.seek(0)
        
        while self.wal_file.tell() < wal_size:
            header = self.wal_file.read(6)
            if not header or len(header) < 6:
                break
            key_len, value_len = struct.unpack('>HI', header)
            key_bytes = self.wal_file.read(key_len)
            value_bytes = self.wal_file.read(value_len)
            
            record = header + key_bytes + value_bytes
            self.file.write(record)
            
        self.file.flush()
        self.wal_file.close()
        self.wal_file = open(self.wal_filename, "w+b")
        print("🎉 Recovery complete! Main database restored.")

    def put(self, key: str, value: str):
        """Saves data safely using a Thread Lock to prevent multi-user corruption."""
        # NEW: Acquire the lock. If another user is writing, this user waits in line automatically.
        with self.lock:
            key_bytes = key.encode('utf-8')
            value_bytes = value.encode('utf-8')
            
            header = struct.pack('>HI', len(key_bytes), len(value_bytes))
            record = header + key_bytes + value_bytes
            
            # 1. Write to WAL
            self.wal_file.write(record)
            self.wal_file.flush()
            
            # 2. Write to main disk database file
            offset = self.file.tell()
            self.file.write(record)
            self.file.flush()
            
            # 3. Clear WAL entry
            self.wal_file.seek(0)
            self.wal_file.truncate(0)
            
            # 4. Update memory index
            self.index[key] = offset
            
            # 5. Put it in the LRU Cache
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            
            if len(self.cache) > self.cache_capacity:
                evicted_key, _ = self.cache.popitem(last=False)
                print(f"🗑️ Cache Full! Evicted '{evicted_key}' from memory.")
                
            print(f"🔒 [Thread {threading.current_thread().name}] Saved '{key}' safely!")
        # The lock is automatically released here when exiting the 'with' block

    def get(self, key: str) -> str:
        """Looks up a key. Thread-safe reading using the lock."""
        with self.lock:
            # 1. Check the LRU Cache first
            if key in self.cache:
                print(f"⚡ [Thread {threading.current_thread().name}] Cache HIT for '{key}'")
                self.cache.move_to_end(key)
                return self.cache[key]
                
            # 2. Cache Miss! Look at disk index
            if key not in self.index:
                return None
                
            print(f"🐢 [Thread {threading.current_thread().name}] Cache MISS for '{key}', reading disk...")
            offset = self.index[key]
            self.file.seek(offset)
            
            header = self.file.read(6)
            key_len, value_len = struct.unpack('>HI', header)
            self.file.seek(offset + 6 + key_len)
            value_bytes = self.file.read(value_len)
            value = value_bytes.decode('utf-8')
            
            # 3. Save to cache
            self.cache[key] = value
            if len(self.cache) > self.cache_capacity:
                evicted_key, _ = self.cache.popitem(last=False)
                print(f"🗑️ Cache Full! Evicted '{evicted_key}' from memory.")
                
            return value

    def _load_index(self):
        """Scans the main file to build the fast RAM memory map."""
        self.file.seek(0, os.SEEK_END)
        file_size = self.file.tell()
        self.file.seek(0)
        
        while self.file.tell() < file_size:
            current_offset = self.file.tell()
            header = self.file.read(6)
            if not header or len(header) < 6:
                break
            key_len, value_len = struct.unpack('>HI', header)
            key_bytes = self.file.read(key_len)
            key = key_bytes.decode('utf-8')
            self.index[key] = current_offset
            self.file.seek(value_len, os.SEEK_CUR)

    def close(self):
        self.wal_file.close()
        self.file.close()

# NEW: Worker function to simulate multiple users slamming the database at the same time
def simulate_user(db, user_id):
    for i in range(2):
        db.put(f"user_{user_id}_key_{i}", f"value_{i}")
        time.sleep(0.1)  # Simulate small gap between requests
        db.get(f"user_{user_id}_key_{i}")

if __name__ == "__main__":
    db = SimpleStorageEngine(cache_capacity=5)
    
    print("--- Starting Concurrency Simulation (Multiple Threads Running At Once) ---")
    
    threads = []
    # Create 3 separate virtual users running at the exact same time
    for name in ["Alice", "Bob", "Charlie"]:
        t = threading.Thread(target=simulate_user, args=(db, name), name=name)
        threads.append(t)
        t.start()
        
    # Wait for all users to finish up before closing the DB
    for t in threads:
        t.join()
        
    db.close()
    print("--- Simulation Finished Safely Without Corruption! ---")