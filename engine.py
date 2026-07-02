import os
import struct
import threading
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
        
        self.lock = threading.Lock()
        
        self._recover_from_wal()
        self._load_index()

    def _recover_from_wal(self):
        """Scans the WAL file on startup for automatic crash recovery using 7-byte headers."""
        self.wal_file.seek(0, os.SEEK_END)
        wal_size = self.wal_file.tell()
        if wal_size == 0:
            return
            
        print("⚠️ Database did not close cleanly! Starting Crash Recovery via WAL...")
        self.wal_file.seek(0)
        
        while self.wal_file.tell() < wal_size:
            header = self.wal_file.read(7)
            if not header or len(header) < 7:
                break
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            key_bytes = self.wal_file.read(key_len)
            value_bytes = self.wal_file.read(value_len)
            
            record = header + key_bytes + value_bytes
            self.file.write(record)
            
        self.file.flush()
        self.wal_file.close()
        self.wal_file = open(self.wal_filename, "w+b")
        print("🎉 Recovery complete! Main database restored.")

    def put(self, key: str, value: str):
        """Saves data safely using a Thread Lock and 7-byte active record headers."""
        with self.lock:
            key_bytes = key.encode('utf-8')
            value_bytes = value.encode('utf-8')
            
            # Record Type 0 = Active Data
            header = struct.pack('>BHI', 0, len(key_bytes), len(value_bytes))
            record = header + key_bytes + value_bytes
            
            self.wal_file.write(record)
            self.wal_file.flush()
            
            offset = self.file.tell()
            self.file.write(record)
            self.file.flush()
            
            self.wal_file.seek(0)
            self.wal_file.truncate(0)
            
            self.index[key] = offset
            
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            
            if len(self.cache) > self.cache_capacity:
                evicted_key, _ = self.cache.popitem(last=False)
                
            print(f"🔒 [Thread {threading.current_thread().name}] Saved '{key}' safely!")

    def delete(self, key: str):
        """NEW: Appends a Tombstone record to disk to mark a key as deleted."""
        with self.lock:
            if key not in self.index:
                print(f"ℹ️ Key '{key}' not found. Nothing to delete.")
                return

            key_bytes = key.encode('utf-8')
            # Record Type 1 = Tombstone (Value size is 0 bytes)
            header = struct.pack('>BHI', 1, len(key_bytes), 0)
            record = header + key_bytes

            # 1. Write Tombstone to WAL
            self.wal_file.write(record)
            self.wal_file.flush()

            # 2. Append Tombstone to main database file
            self.file.write(record)
            self.file.flush()

            # 3. Clear WAL
            self.wal_file.seek(0)
            self.wal_file.truncate(0)

            # 4. Evict from memory maps instantly
            if key in self.index:
                del self.index[key]
            if key in self.cache:
                del self.cache[key]

            print(f"🪦 [Thread {threading.current_thread().name}] Placed Tombstone for '{key}'!")

    def get(self, key: str) -> str:
        """Looks up a key. Thread-safe reading using 7-byte layout."""
        with self.lock:
            if key in self.cache:
                return self.cache[key]
                
            if key not in self.index:
                return None
                
            offset = self.index[key]
            self.file.seek(offset)
            
            header = self.file.read(7)
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            
            # Defensive check: if it's somehow a tombstone, return None
            if record_type == 1:
                return None
                
            self.file.seek(offset + 7 + key_len)
            value_bytes = self.file.read(value_len)
            value = value_bytes.decode('utf-8')
            
            self.cache[key] = value
            if len(self.cache) > self.cache_capacity:
                self.cache.popitem(last=False)
                
            return value

    def compact(self):
        """NEW: Reclaims wasted hard drive space by purging dead keys and old duplicates."""
        print("\n🧹 Starting Disk Compaction Engine...")
        with self.lock:
            compaction_file_name = "compacted.db.tmp"
            
            # Close existing handle to ensure everything is flushed to current database
            self.file.close()
            
            # Read from old file, write fresh data to new temporary file
            with open(self.db_filename, "rb") as old_file, open(compaction_file_name, "wb") as new_file:
                new_index = {}
                old_file.seek(0, os.SEEK_END)
                file_size = old_file.tell()
                old_file.seek(0)
                
                while old_file.tell() < file_size:
                    current_offset = old_file.tell()
                    header = old_file.read(7)
                    if not header or len(header) < 7:
                        break
                        
                    record_type, key_len, value_len = struct.unpack('>BHI', header)
                    key_bytes = old_file.read(key_len)
                    key = key_bytes.decode('utf-8')
                    
                    # Read value bytes out of the way to move file pointer accurately
                    value_bytes = old_file.read(value_len)
                    
                    # Core Logic: Only copy the record if it matches our active memory map offset!
                    # This completely drops tombstones and old versions of overwritten keys.
                    if key in self.index and self.index[key] == current_offset:
                        new_offset = new_file.tell()
                        new_record = header + key_bytes + value_bytes
                        new_file.write(new_record)
                        new_index[key] = new_offset
            
            # Swap old uncompacted file out for the clean compacted one
            os.remove(self.db_filename)
            os.rename(compaction_file_name, self.db_filename)
            
            # Reopen the main file handle and load the updated clean index map
            self.file = open(self.db_filename, "a+b")
            self.index = new_index
            print(f"🎉 Compaction Finished! New database index size: {len(self.index)} active items.\n")

    def _load_index(self):
        """Scans the main file to build the fast RAM memory map with Tombstone handling."""
        self.file.seek(0, os.SEEK_END)
        file_size = self.file.tell()
        self.file.seek(0)
        
        while self.file.tell() < file_size:
            current_offset = self.file.tell()
            header = self.file.read(7)
            if not header or len(header) < 7:
                break
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            key_bytes = self.file.read(key_len)
            key = key_bytes.decode('utf-8')
            
            if record_type == 1: # Tombstone encountered
                if key in self.index:
                    del self.index[key]
            else: # Active data record
                self.index[key] = current_offset
                
            self.file.seek(value_len, os.SEEK_CUR)

    def close(self):
        if not self.file.closed:
            self.file.close()
        if not self.wal_file.closed:
            self.wal_file.close()

if __name__ == "__main__":
    # Clean up files from previous project phases for our new protocol
    for f in ["data.db", "wal.log"]:
        if os.path.exists(f): os.remove(f)

    db = SimpleStorageEngine()
    
    print("--- 1. Testing Overwrites & Deletions ---")
    db.put("username", "player1")
    db.put("username", "player2") # Overwrite old data chunk
    db.put("score", "100")
    db.delete("score")            # Drop data chunk via Tombstone
    
    print(f"Current Value for 'username': {db.get('username')}")
    print(f"Current Value for 'score': {db.get('score')}")
    
    print(f"Physical file size before compaction: {os.path.getsize('data.db')} bytes")
    
    # 2. Trigger Compaction Engine to sweep dead weights
    db.compact()
    
    print(f"Physical file size after compaction: {os.path.getsize('data.db')} bytes")
    print(f"Value check post-compaction: {db.get('username')}")
    
    db.close()