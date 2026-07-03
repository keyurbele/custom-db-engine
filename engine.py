import os
import struct
import threading
import mmap
from collections import OrderedDict

PAGE_SIZE = 4096

# ==========================================
# 🌲 DATA STRUCTURE: FIXED B+ TREE INDEX
# ==========================================
class BPlusNode:
    def __init__(self, is_leaf=False):
        self.is_leaf = is_leaf
        self.keys = []
        self.values = []  # If leaf: disk offsets. If internal: child BPlusNodes.
        self.next = None  # Pointer to next leaf for sequential scans

class BPlusTreeIndex:
    def __init__(self, degree=4):
        self.root = BPlusNode(is_leaf=True)
        self.degree = degree

    def search(self, key):
        """Traverses nodes safely using strict upper-bound comparisons."""
        current = self.root
        while not current.is_leaf:
            i = 0
            while i < len(current.keys) and key >= current.keys[i]:
                i += 1
            current = current.values[i]
        
        if key in current.keys:
            return current.values[current.keys.index(key)]
        return None

    def insert(self, key, offset):
        """Inserts a key and correctly handles structural root splits."""
        root = self.root
        if len(root.keys) == self.degree - 1:
            new_root = BPlusNode(is_leaf=False)
            new_root.values.append(self.root)
            self._split_child(new_root, 0, self.root)
            self.root = new_root
        self._insert_non_full(self.root, key, offset)

    def delete(self, key):
        """Removes a key pointer from the leaf tracker."""
        current = self.root
        while not current.is_leaf:
            i = 0
            while i < len(current.keys) and key >= current.keys[i]:
                i += 1
            current = current.values[i]
        if key in current.keys:
            idx = current.keys.index(key)
            current.keys.pop(idx)
            current.values.pop(idx)

    def range_search(self, start_key, end_key):
        """Traverses linked leaves to pull sorted ranges."""
        current = self.root
        while not current.is_leaf:
            i = 0
            while i < len(current.keys) and start_key >= current.keys[i]:
                i += 1
            current = current.values[i]
        
        results = []
        while current:
            for i, key in enumerate(current.keys):
                if start_key <= key <= end_key:
                    results.append((key, current.values[i]))
                elif key > end_key:
                    return results
            current = current.next
        return results

    def _insert_non_full(self, node, key, offset):
        if node.is_leaf:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1
            if i < len(node.keys) and node.keys[i] == key:
                node.values[i] = offset
            else:
                node.keys.insert(i, key)
                node.values.insert(i, offset)
        else:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            if len(node.values[i].keys) == self.degree - 1:
                self._split_child(node, i, node.values[i])
                if key >= node.keys[i]:
                    i += 1
            self._insert_non_full(node.values[i], key, offset)

    def _split_child(self, parent, i, child):
        """FIXED: Keeps keys properly balanced on both leaf and internal levels."""
        mid = len(child.keys) // 2
        split_key = child.keys[mid]
        
        new_node = BPlusNode(is_leaf=child.is_leaf)
        parent.keys.insert(i, split_key)
        parent.values.insert(i + 1, new_node)
        
        if child.is_leaf:
            # Leaves MUST keep a copy of the split key on the right side
            new_node.keys = child.keys[mid:]
            new_node.values = child.values[mid:]
            child.keys = child.keys[:mid]
            child.values = child.values[:mid]
            new_node.next = child.next
            child.next = new_node
        else:
            # Internal nodes push the split key up completely
            new_node.keys = child.keys[mid + 1:]
            new_node.values = child.values[mid + 1:]
            child.keys = child.keys[:mid]
            child.values = child.values[:mid + 1]

# ==========================================
# 🗄️ STORAGE ENGINE
# ==========================================
class SimpleStorageEngine:
    def __init__(self, db_filename="data.db", wal_filename="wal.log", cache_capacity=3):
        self.db_filename = db_filename
        self.wal_filename = wal_filename
        self.cache_capacity = cache_capacity
        self.lock = threading.Lock()
        
        self.index = BPlusTreeIndex(degree=4)
        self.cache = OrderedDict()
        
        if not os.path.exists(self.db_filename):
            with open(self.db_filename, "wb") as f:
                f.write(b'\x00' * PAGE_SIZE)
        
        self.db_file = open(self.db_filename, "r+b")
        self.db_size = os.path.getsize(self.db_filename)
        self.mm = mmap.mmap(self.db_file.fileno(), 0, access=mmap.ACCESS_WRITE)
        self.next_free_offset = self._find_next_free_offset()
        self.wal_file = open(self.wal_filename, "a+b")
        
        self._recover_from_wal()
        self._load_index()

    def _find_next_free_offset(self):
        offset = 0
        while offset < self.db_size:
            header = self.mm[offset:offset+7]
            if len(header) < 7 or header == b'\x00'*7:
                return offset
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            offset += 7 + key_len + value_len
        return offset

    def _ensure_capacity(self, needed_bytes):
        if self.next_free_offset + needed_bytes > self.db_size:
            pages_needed = ((self.next_free_offset + needed_bytes - self.db_size) // PAGE_SIZE) + 1
            new_size = self.db_size + (pages_needed * PAGE_SIZE)
            self.mm.close()
            self.db_file.truncate(new_size)
            self.mm = mmap.mmap(self.db_file.fileno(), 0, access=mmap.ACCESS_WRITE)
            self.db_size = new_size

    def _recover_from_wal(self):
        self.wal_file.seek(0, os.SEEK_END)
        wal_size = self.wal_file.tell()
        if wal_size == 0: return
        self.wal_file.seek(0)
        while self.wal_file.tell() < wal_size:
            header = self.wal_file.read(7)
            if not header or len(header) < 7: break
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            key_bytes = self.wal_file.read(key_len)
            value_bytes = self.wal_file.read(value_len)
            record = header + key_bytes + value_bytes
            self._ensure_capacity(len(record))
            self.mm[self.next_free_offset : self.next_free_offset + len(record)] = record
            self.next_free_offset += len(record)
        self.mm.flush()
        self.wal_file.close()
        self.wal_file = open(self.wal_filename, "w+b")

    def put(self, key: str, value: str):
        with self.lock:
            key_bytes = key.encode('utf-8')
            value_bytes = value.encode('utf-8')
            header = struct.pack('>BHI', 0, len(key_bytes), len(value_bytes))
            record = header + key_bytes + value_bytes
            
            self.wal_file.write(record)
            self.wal_file.flush()
            
            self._ensure_capacity(len(record))
            offset = self.next_free_offset
            self.mm[offset : offset + len(record)] = record
            self.next_free_offset += len(record)
            
            self.wal_file.seek(0)
            self.wal_file.truncate(0)
            self.index.insert(key, offset)
            
            if key in self.cache: self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.cache_capacity: self.cache.popitem(last=False)

    def delete(self, key: str):
        with self.lock:
            if self.index.search(key) is None: return
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
            self.index.delete(key)
            if key in self.cache: del self.cache[key]

    def get(self, key: str) -> str:
        with self.lock:
            if key in self.cache: return self.cache[key]
            offset = self.index.search(key)
            if offset is None: return None
            header = self.mm[offset : offset + 7]
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            if record_type == 1: return None
            val_start = offset + 7 + key_len
            value = self.mm[val_start : val_start + value_len].decode('utf-8')
            self.cache[key] = value
            if len(self.cache) > self.cache_capacity: self.cache.popitem(last=False)
            return value

    def get_range(self, start_key: str, end_key: str):
        with self.lock:
            matched_offsets = self.index.range_search(start_key, end_key)
            results = {}
            for key, offset in matched_offsets:
                header = self.mm[offset : offset + 7]
                record_type, key_len, value_len = struct.unpack('>BHI', header)
                if record_type != 1:
                    val_start = offset + 7 + key_len
                    results[key] = self.mm[val_start : val_start + value_len].decode('utf-8')
            return results

    def compact(self):
        with self.lock:
            compaction_file_name = "compacted.db.tmp"
            with open(compaction_file_name, "wb") as f:
                f.write(b'\x00' * PAGE_SIZE)
            with open(compaction_file_name, "r+b") as temp_file:
                temp_mm = mmap.mmap(temp_file.fileno(), 0, access=mmap.ACCESS_WRITE)
                temp_offset = 0
                new_index = BPlusTreeIndex(degree=4)
                curr_scan = 0
                while curr_scan < self.next_free_offset:
                    header = self.mm[curr_scan : curr_scan + 7]
                    if len(header) < 7 or header == b'\x00'*7: break
                    record_type, key_len, value_len = struct.unpack('>BHI', header)
                    key = self.mm[curr_scan + 7 : curr_scan + 7 + key_len].decode('utf-8')
                    value_bytes = self.mm[curr_scan + 7 + key_len : curr_scan + 7 + key_len + value_len]
                    if self.index.search(key) == curr_scan:
                        record = header + self.mm[curr_scan + 7 : curr_scan + 7 + key_len] + value_bytes
                        if temp_offset + len(record) > temp_mm.size():
                            temp_mm.close()
                            temp_file.truncate(temp_file.tell() + PAGE_SIZE)
                            temp_mm = mmap.mmap(temp_file.fileno(), 0, access=mmap.ACCESS_WRITE)
                        temp_mm[temp_offset : temp_offset + len(record)] = record
                        new_index.insert(key, temp_offset)
                        temp_offset += len(record)
                    curr_scan += 7 + key_len + value_len
                temp_mm.flush()
                temp_mm.close()
            self.mm.close()
            self.db_file.close()
            os.remove(self.db_filename)
            os.rename(compaction_file_name, self.db_filename)
            self.db_file = open(self.db_filename, "r+b")
            self.db_size = os.path.getsize(self.db_filename)
            self.mm = mmap.mmap(self.db_file.fileno(), 0, access=mmap.ACCESS_WRITE)
            self.index = new_index
            self.next_free_offset = temp_offset

    def _load_index(self):
        offset = 0
        while offset < self.db_size:
            header = self.mm[offset:offset+7]
            if len(header) < 7 or header == b'\x00'*7: break
            record_type, key_len, value_len = struct.unpack('>BHI', header)
            key = self.mm[offset+7 : offset+7+key_len].decode('utf-8')
            if record_type == 1:
                self.index.delete(key)
            else:
                self.index.insert(key, offset)
            offset += 7 + key_len + value_len

    def close(self):
        with self.lock:
            if hasattr(self, 'mm') and self.mm:
                try: self.mm.close()
                except: pass
            if hasattr(self, 'db_file') and not self.db_file.closed: self.db_file.close()
            if hasattr(self, 'wal_file') and not self.wal_file.closed: self.wal_file.close()

if __name__ == "__main__":
    for f in ["data.db", "wal.log"]:
        if os.path.exists(f): os.remove(f)
    db = SimpleStorageEngine()
    db.put("user_10", "Alice")
    db.put("user_45", "Bob")
    db.put("user_25", "Charlie")
    print("Range scan test:", db.get_range("user_10", "user_50"))
    db.close()