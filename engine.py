import os
import struct

class SimpleStorageEngine:
    def __init__(self, db_filename="data.db"):
        self.db_filename = db_filename
        self.file = open(self.db_filename, "a+b")
        self.index = {}
        self._load_index()

    def put(self, key: str, value: str):
        """Saves a key-value pair to the disk binary file."""
        key_bytes = key.encode('utf-8')
        value_bytes = value.encode('utf-8')
        
        key_len = len(key_bytes)
        value_len = len(value_bytes)
        
        header = struct.pack('>HI', key_len, value_len)
        offset = self.file.tell()
        
        record = header + key_bytes + value_bytes
        self.file.write(record)
        self.file.flush() 
        
        self.index[key] = offset
        print(f"🎉 Successfully saved '{key}' at byte position {offset}!")

    def get(self, key: str) -> str:
        """Looks up a key in RAM, goes to that exact byte spot on disk, and reads it."""
        if key not in self.index:
            return None
        
        offset = self.index[key]
        self.file.seek(offset)
        
        header = self.file.read(6)
        if not header:
            return None
            
        key_len, value_len = struct.unpack('>HI', header)
        self.file.seek(offset + 6 + key_len)
        value_bytes = self.file.read(value_len)
        
        return value_bytes.decode('utf-8')

    def _load_index(self):
        """Scans the entire file on startup to rebuild the index in RAM."""
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
            self.file.seek(value_len, os.seek_cur)
            
        print(f"Loaded index. Found {len(self.index)} existing keys in database file.")

    def close(self):
        self.file.close()

if __name__ == "__main__":
    db = SimpleStorageEngine()
    db.put("TAMU", "Top Priority University")
    db.put("status", "Building a database engine from scratch!")
    
    print("\n--- Testing Retrieval ---")
    print("Result for 'TAMU':", db.get("TAMU"))
    print("Result for 'status':", db.get("status"))
    db.close()