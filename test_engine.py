import os
import unittest
from engine import SimpleStorageEngine

class TestSimpleStorageEngine(unittest.TestCase):
    def setUp(self):
        """Clean environment before every single test run."""
        for f in ["test_data.db", "test_wal.log"]:
            if os.path.exists(f):
                os.remove(f)
        self.db = SimpleStorageEngine(db_filename="test_data.db", wal_filename="test_wal.log")

    def tearDown(self):
        """Clean up filesystem footprints post testing."""
        self.db.close()
        for f in ["test_data.db", "test_wal.log"]:
            if os.path.exists(f):
                os.remove(f)

    def test_put_and_get(self):
        """Verify basic storage write/read cycles."""
        self.db.put("test_key", "test_value")
        self.assertEqual(self.db.get("test_key"), "test_value")

    def test_tombstone_deletion(self):
        """Verify that tombstones properly hide deleted keys."""
        self.db.put("delete_me", "ghost_data")
        self.db.delete("delete_me")
        self.assertIsNone(self.db.get("delete_me"))

    def test_compaction_reclaims_space(self):
        """Verify that compaction physically shrinks the database file."""
        # Write initial data, overwrite it, and add then delete another key
        self.db.put("key1", "initial_version")
        self.db.put("key1", "updated_version")
        self.db.put("key2", "to_be_deleted")
        self.db.delete("key2")
        
        size_before = os.path.getsize("test_data.db")
        
        # Trigger compaction routine
        self.db.compact()
        
        size_after = os.path.getsize("test_data.db")
        
        # Assertions
        self.assertLess(size_after, size_before)
        self.assertEqual(self.db.get("key1"), "updated_version")
        self.assertIsNone(self.db.get("key2"))

if __name__ == "__main__":
    unittest.main()