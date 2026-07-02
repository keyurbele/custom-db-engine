import os
import unittest
from engine import SimpleStorageEngine

class TestStorageEngine(unittest.TestCase):
    def setUp(self):
        # Use clean files for testing
        self.db_name = "test_data.db"
        self.wal_name = "test_wal.log"
        # Clean up any leftover test files from previous runs
        if os.path.exists(self.db_name): os.remove(self.db_name)
        if os.path.exists(self.wal_name): os.remove(self.wal_name)
        
        self.db = SimpleStorageEngine(db_filename=self.db_name, wal_filename=self.wal_name, cache_capacity=2)

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_name): os.remove(self.db_name)
        if os.path.exists(self.wal_name): os.remove(self.wal_name)

    def test_put_and_get(self):
        """Test basic saving and retrieving functionality."""
        self.db.put("hello", "world")
        self.assertEqual(self.db.get("hello"), "world")

    def test_cache_eviction(self):
        """Test if the LRU cache correctly evicts keys when capacity is exceeded."""
        self.db.put("k1", "v1")
        self.db.put("k2", "v2")
        self.db.put("k3", "v3") # Should evict k1 because capacity is 2
        
        # k3 should be a cache hit, k1 should read from disk but still return the correct value
        self.assertEqual(self.db.get("k3"), "v3")
        self.assertEqual(self.db.get("k1"), "v1")

if __name__ == "__main__":
    unittest.main()