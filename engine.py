import os
import struct

class SimpleStorageEngine:
    def __init__(self, db_filename="data.db", wal_filename="wal.log"):
        self.db_filename = db_filename
        self.wal_filename = wal_filename
        
        # Open the main database file (Binary Append/Read mode)
        self.file = open(self.db_filename, "a+b")
        
        # Open the Write-Ahead Log (WAL) file (Binary Append/Read mode)
        self.wal_file = open(self.wal_filename, "a+b")
        
        self.index = {}
        
        # CRITICAL SYSTEMS STEP: Before loading anything, check if we crashed last time!
        self._recover_from_wal()
        
        # Load the index from the main data file into memory
        self._load_index()

    def _recover_from_wal(self):
        """Scans the WAL file on startup. If it finds data, it means the DB crashed last time!"""
        self.wal_file.seek(0, os.SEEK_END)
        wal_size = self.wal_file.tell()
        
        if wal_size == 0:
            return  # No WAL data found, database closed cleanly last time.
            
        print("⚠️ Database did not close cleanly last time! Starting Crash Recovery via WAL...")
        self.wal_file.seek(0)
        
        # Read the logs from the WAL scratchpad and rewrite them safely to the main DB
        while self.wal_file.tell() < wal_size:
            header = self.wal_file.read(6)
            if not header or len(header) < 6:
                break
            key_len, value_len = struct.unpack('>HI', header)
            
            key_bytes = self.wal_file.read(key_len)
            value_bytes = self.wal_file.read(value_len)
            
            # Re-write this data to the main database file to ensure it's safe
            offset = self.file.tell()
            record = header + key_bytes + value_bytes
            self.file.write(record)
            
        self.file.flush()
        
        # Clear the WAL file since we successfully recovered all lost data
        self.wal_file.close()
        self.wal_file = open(self.wal_filename, "w+b") # Overwrites file to size 0
        print("🎉 Recovery complete! Main database restored to a healthy state.")

    def put(self, key: str, value: str):
        """Saves data by writing to the WAL first, then updating the main database file."""
        key_bytes = key.encode('utf-8')
        value_bytes = value.encode('utf-8')
        
        key_len = len(key_bytes)
        value_len = len(value_bytes)
        header = struct.pack('>HI', key_len, value_len)
        record = header + key_bytes + value_bytes
        
        # STEP 1: Write to the Write-Ahead Log first (Safety net)
        self.wal_file.write(record)
        self.wal_file.flush()
        
        # STEP 2: Write to the main database storage file
        offset = self.file.tell()
        self.file.write(record)
        self.file.flush()
        
        # STEP 3: Clear the WAL entry because the main database safely received it
        # In a full system, we clear the WAL periodically, but for now, we reset it
        self.wal_file.seek(0)
        self.wal_file.truncate(0)
        
        # STEP 4: Update our fast memory index
        self.index[key] = offset
        print(f"💾 Saved '{key}' -> WAL logged & Data written to disk offset {offset}!")

    def get(self, key: str) -> str:
        """Looks up a key in RAM index, grabs it instantly from the binary file."""
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
        """Safely close files and clear the WAL log."""
        self.wal_file.seek(0)
        self.wal_file.truncate(0)
        self.wal_file.close()
        self.file.close()

if __name__ == "__main__":
    db = SimpleStorageEngine()
    
    # Let's test writing with our new WAL system
    db.put("University_Goal", "Texas A&M University (TAMU)")
    db.put("Project_Stage", "Phase 2: Write-Ahead Log Completed")
    
    print("\n--- Testing WAL Protected Retrieval ---")
    print("Goal:", db.get("University_Goal"))
    print("Stage:", db.get("Project_Stage"))
    
    db.close()