import os
import struct
from collections import OrderedDict

class SimpleStorageEngine:
    def __init__(self, db_filename="data.db", wal_filename="wal.log", cache_capacity=3):
        self.db_filename = db_filename
        self.wal_filename = wal_filename
        
        self.file = open(self.db_filename, "a+b")
        self.wal_file = open(self.wal_filename, "a+b")
        
        self.index = {}
        
        # NEW: Initialize our LRU Cache with a limited capacity (e.g., max 3 items in memory)
        self.cache = OrderedDict()
        self.cache_capacity = cache_capacity
        
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
        """Saves data by writing to WAL, main disk, and updating the LRU cache."""
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
        
        # 5. NEW: Put it in the LRU Cache (and handle eviction if full!)
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        
        if len(self.cache) > self.cache_capacity:
            # Pop the oldest item (the first item in OrderedDict)
            evicted_key, _ = self.cache.popitem(last=False)
            print(f"🗑️ Cache Full! Evicted '{evicted_key}' from memory to make room.")
            
        print(f"💾 Saved '{key}' -> Written to disk and cached in memory.")

    def get(self, key: str) -> str:
        """Looks up a key. Hits the fast RAM Cache first. If it misses, reads from disk."""
        # 1. NEW: Check the LRU Cache first (Cache Hit!)
        if key in self.cache:
            print(f"⚡ Cache HIT! Retrieved '{key}' instantly from memory.")
            self.cache.move_to_end(key) # Mark as recently used
            return self.cache[key]
            
        # 2. Cache Miss! We must look at our disk index
        if key not in self.index:
            return None
            
        print(f"🐢 Cache MISS! Reading '{key}' from slow disk hard drive...")
        offset = self.index[key]
        self.file.seek(offset)
        
        header = self.file.read(6)
        key_len, value_len = struct.unpack('>HI', header)
        self.file.seek(offset + 6 + key_len)
        value_bytes = self.file.read(value_len)
        value = value_bytes.decode('utf-8')
        
        # 3. NEW: Save it to the cache so the next read is instant!
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

if __name__ == "__main__":
    # We set cache capacity to 2 items to easily test eviction!
    db = SimpleStorageEngine(cache_capacity=2)
    
    print("--- 1. Writing 3 keys (Cache capacity is 2) ---")
    db.put("key1", "apple")
    db.put("key2", "banana")
    db.put("key3", "cherry") # This should kick "key1" out of the cache!
    
    print("\n--- 2. Reading keys to test Cache Hits vs Misses ---")
    print("Result:", db.get("key3")) # Should be a Cache HIT (still in cache)
    print("Result:", db.get("key1")) # Should be a Cache MISS (was evicted, must read disk)
    print("Result:", db.get("key1")) # Should now be a Cache HIT (pulled back into cache!)
    
    db.close()