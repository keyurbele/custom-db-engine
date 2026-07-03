import os
import unittest
import mmap
from engine import SimpleStorageEngine, PAGE_SIZE

class TestSimpleStorageEngine(unittest.TestCase):
    def setUp(self):
        for f in ["test_data.db", "test_wal.log"]:
            if os.path.exists(f): os.remove(f)
        self.db = SimpleStorageEngine(db_filename="test_data.db", wal_filename="test_wal.log")

    def tearDown(self):
        self.db.close()
        for f in ["test_data.db", "test_wal.log"]:
            if os.path.exists(f): os.remove(f)

    def test_mmap_initialization(self):
        """Verify the database initializes with a valid memory map and page structure."""
        self.assertTrue(hasattr(self.db, 'mm'))
        self.assertIsInstance(self.db.mm, mmap.mmap)
        self.assertEqual(self.db.db_size, PAGE_SIZE)

    def test_put_and_get_via_mmap(self):
        """Verify data can be written and read directly through memory slices."""
        self.db.put("cloud_key", "cloud_value")
        self.assertEqual(self.db.get("cloud_key"), "cloud_value")

    def test_page_auto_allocation(self):
        """Verify the engine dynamically allocates new 4KB pages when data overflows."""
        initial_size = self.db.db_size
        
        # Write a massive value to force page scaling past the initial 4KB boundary
        large_value = "X" * 5000
        self.db.put("large_key", large_value)
        
        # Assert database grew by at least one page size
        self.assertGreater(self.db.db_size, initial_size)
        self.assertEqual(self.db.get("large_key"), large_value)

    def test_mmap_compaction(self):
        """Verify memory map compaction strips dead records cleanly."""
        self.db.put("k1", "v1")
        self.db.put("k1", "v2") # Overwrite
        self.db.delete("k1")   # Tombstone
        
        self.db.compact()
        self.assertIsNone(self.db.get("k1"))

if __name__ == "__main__":
    unittest.main()