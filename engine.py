import os
import struct
import threading
import mmap
from collections import OrderedDict

PAGE_SIZE = 4096  # Standard hardware page size (4KB)

class SimpleStorageEngine:
    def __init__(self, db_filename="data.db", wal_filename="wal.log", cache_capacity=3):
        self.db_filename = db_filename
        self.wal_filename = wal_filename
        self.cache_capacity = cache_capacity
        
        self.lock = threading.Lock()
        self.index = {}
        self.cache = OrderedDict()
        
        # 1. Initialize or open the main database file
        if not os.path.exists(self.db_filename):
            # Pre-allocate exactly 1 Page (4096 bytes) filled with zeroes
            with open(self.db_filename, "wb") as f:
                f.write(b'\x00' * PAGE_SIZE)
        
        self.db_file = open(self.db_filename, "r+b")
        self.db_size = os.path.getsize(self.db_filename)
        
        # Memory-map the database file
        self.mm = mmap.mmap(self.db_file.fileno(), 0, access=mmap.ACCESS_WRITE)
        
        # Track where the next free byte is inside our page structure
        self.next_free_offset = self._find_next_free_offset()
        
        # 2. Open standard file handle for WAL (Write-Ahead Log)
        self.wal_file = open(self.wal_filename, "a+b")
        
        self._recover_from_wal()
        self._load_index()

    def _find_next_free_offset(self):
        """Scans memory map backwards to find where valid data ends."""
        self.mm.seek(0)
        offset = 0
        while offset < self.db_size:
            header = self.mm[offset:offset+7]
            if len(header) < 7 or header == b'\x00'*7:
                return offset
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            # Skip past header + key + value to find the next record boundary
            offset += 7 + key_len + value_len
        return offset

    def _ensure_capacity(self, needed_bytes):
        """NEW: Automatically allocates new 4KB pages if we run out of space."""
        if self.next_free_offset + needed_bytes > self.db_size:
            # Calculate how many new pages are needed
            pages_needed = ((self.next_free_offset + needed_bytes - self.db_size) // PAGE_SIZE) + 1
            new_size = self.db_size + (pages_needed * PAGE_SIZE)
            
            # Resize the physical file and remap the memory layout
            self.mm.close()
            self.db_file.truncate(new_size)
            self.mm = mmap.mmap(self.db_file.fileno(), 0, access=mmap.ACCESS_WRITE)
            self.db_size = new_size
            print(f"📄 Allocated {pages_needed} new 4KB page(s). Total DB Size: {self.db_size} bytes.")

    def _recover_from_wal(self):
        """Applies missing transactions from the WAL log back into the mmap structure."""
        self.wal_file.seek(0, os.SEEK_END)
        wal_size = self.wal_file.tell()
        if wal_size == 0:
            return
            
        print("⚠️ Database crash detected! Replaying WAL records into Memory Map...")
        self.wal_file.seek(0)
        
        while self.wal_file.tell() < wal_size:
            header = self.wal_file.read(7)
            if not header or len(header) < 7:
                break
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            key_bytes = self.wal_file.read(key_len)
            value_bytes = self.wal_file.read(value_len)
            
            record = header + key_bytes + value_bytes
            self._ensure_capacity(len(record))
            
            # Direct memory slice write via mmap instead of file.write()
            self.mm[self.next_free_offset : self.next_free_offset + len(record)] = record
            self.next_free_offset += len(record)
            
        self.mm.flush()
        self.wal_file.close()
        self.wal_file = open(self.wal_filename, "w+b")
        print("🎉 Recovery complete via Memory Mapping.")

    def put(self, key: str, value: str):
        """Writes data via low-latency Memory Mapping slices."""
        with self.lock:
            key_bytes = key.encode('utf-8')
            value_bytes = value.encode('utf-8')
            
            header = struct.pack('>BHI', 0, len(key_bytes), len(value_bytes))
            record = header + key_bytes + value_bytes
            
            # 1. Log to WAL first for durability
            self.wal_file.write(record)
            self.wal_file.flush()
            
            # 2. Allocate pages if needed, then copy record into memory map
            self._ensure_capacity(len(record))
            offset = self.next_free_offset
            
            self.mm[offset : offset + len(record)] = record
            self.next_free_offset += len(record)
            
            # 3. Clear WAL
            self.wal_file.seek(0)
            self.wal_file.truncate(0)
            
            # Update RAM index and cache
            self.index[key] = offset
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            
            if len(self.cache) > self.cache_capacity:
                self.cache.popitem(last=False)
                
            print(f"🔒 [mmap Engine] Map Slice Saved '{key}' at offset {offset}")

    def delete(self, key: str):
        """Appends a Tombstone record into the page architecture via mmap."""
        with self.lock:
            if key not in self.index:
                return

            key_bytes = key.encode('utf-8')
            header = struct.pack('>BHI', 1, len(key_bytes), 0)
            record = header + key_bytes

            self.wal_file.write(record)
            self.wal_file.flush()

            self._ensure_capacity(len(record))
            offset = self.next_free_offset
            self.mm[offset : offset + len(record)] = record
            self.next_free_offset += len(record)

            self.wal_file.seek(0)
            self.wal_file.truncate(0)

            if key in self.index: del self.index[key]
            if key in self.cache: del self.cache[key]
            print(f"🪦 [mmap Engine] Placed Tombstone for '{key}'")

    def get(self, key: str) -> str:
        """Reads data straight out of virtual memory mapping, avoiding disk seek calls."""
        with self.lock:
            if key in self.cache:
                return self.cache[key]
                
            if key not in self.index:
                return None
                
            offset = self.index[key]
            header = self.mm[offset : offset + 7]
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            
            if record_type == 1:
                return None
                
            val_start = offset + 7 + key_len
            value_bytes = self.mm[val_start : val_start + value_len]
            value = value_bytes.decode('utf-8')
            
            self.cache[key] = value
            if len(self.cache) > self.cache_capacity:
                self.cache.popitem(last=False)
                
            return value

    def compact(self):
        """Reclaims space inside the page architecture by creating a fresh compacted map."""
        print("\n🧹 Starting Memory-Mapped Compaction Engine...")
        with self.lock:
            compaction_file_name = "compacted.db.tmp"
            
            # Pre-allocate 1 Page for the temporary compaction file
            with open(compaction_file_name, "wb") as f:
                f.write(b'\x00' * PAGE_SIZE)
                
            with open(compaction_file_name, "r+b") as temp_file:
                temp_mm = mmap.mmap(temp_file.fileno(), 0, access=mmap.ACCESS_WRITE)
                temp_offset = 0
                new_index = {}
                
                # Scan through current memory map
                curr_scan = 0
                while curr_scan < self.next_free_offset:
                    header = self.mm[curr_scan : curr_scan + 7]
                    if len(header) < 7 or header == b'\x00'*7:
                        break
                    record_type, key_len, value_len = struct.unpack('>BHI', header)
                    
                    key_bytes = self.mm[curr_scan + 7 : curr_scan + 7 + key_len]
                    key = key_bytes.decode('utf-8')
                    value_bytes = self.mm[curr_scan + 7 + key_len : curr_scan + 7 + key_len + value_len]
                    
                    # Copy only if it matches our active memory offset pointer
                    if key in self.index and self.index[key] == curr_scan:
                        record = header + key_bytes + value_bytes
                        
                        # Grow temp map if it exceeds boundary sizes
                        if temp_offset + len(record) > temp_mm.size():
                            temp_mm.close()
                            temp_file.truncate(temp_file.tell() + PAGE_SIZE)
                            temp_mm = mmap.mmap(temp_file.fileno(), 0, access=mmap.ACCESS_WRITE)
                            
                        temp_mm[temp_offset : temp_offset + len(record)] = record
                        new_index[key] = temp_offset
                        temp_offset += len(record)
                        
                    curr_scan += 7 + key_len + value_len
                
                temp_mm.flush()
                temp_mm.close()
                
            # Close current windows maps and swap file descriptors
            self.mm.close()
            self.db_file.close()
            
            os.remove(self.db_filename)
            os.rename(compaction_file_name, self.db_filename)
            
            # Re-establish new memory mapped handles
            self.db_file = open(self.db_filename, "r+b")
            self.db_size = os.path.getsize(self.db_filename)
            self.mm = mmap.mmap(self.db_file.fileno(), 0, access=mmap.ACCESS_WRITE)
            self.index = new_index
            self.next_free_offset = temp_offset
            print(f"🎉 Compaction Complete! Active Database Size: {self.db_size} bytes.\n")

    def _load_index(self):
        """Quickly crawls the memory map array to initialize index locations inside RAM."""
        offset = 0
        while offset < self.db_size:
            header = self.mm[offset:offset+7]
            if len(header) < 7 or header == b'\x00'*7:
                break
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            key_bytes = self.mm[offset+7 : offset+7+key_len]
            key = key_bytes.decode('utf-8')
            
            if record_type == 1:
                if key in self.index: del self.index[key]
            else:
                self.index[key] = offset
                
            offset += 7 + key_len + value_len

    def close(self):
        with self.lock:
            if hasattr(self, 'mm') and self.mm:
                try:
                    self.mm.flush()
                    self.mm.close()
                except: pass
            if hasattr(self, 'db_file') and not self.db_file.closed:
                self.db_file.close()
            if hasattr(self, 'wal_file') and not self.wal_file.closed:
                self.wal_file.close()

if __name__ == "__main__":
    for f in ["data.db", "wal.log"]:
        if os.path.exists(f): os.remove(f)

    db = SimpleStorageEngine()
    
    print("--- Testing Page Allocation & Memory Mapping ---")
    db.put("user_a", "value_1")
    db.put("user_b", "value_2")
    
    print(f"Read 'user_a' from mmap: {db.get('user_a')}")
    print(f"Current structural disk size: {db.db_size} bytes (1 allocated 4KB Page).")
    
    db.close()