import os
import unittest
from engine import SimpleStorageEngine

class TestSimpleStorageEngine(unittest.TestCase):
    def setUp(self):
        for f in ["test_data.db", "test_wal.log"]:
            if os.path.exists(f): os.remove(f)
        self.db = SimpleStorageEngine(db_filename="test_data.db", wal_filename="test_wal.log")

    def tearDown(self):
        self.db.close()
        for f in ["test_data.db", "test_wal.log"]:
            if os.path.exists(f): os.remove(f)

    def test_bplus_tree_put_and_get(self):
        """Verify point lookups function accurately through the B+ Tree index."""
        self.db.put("key1", "val1")
        self.db.put("key2", "val2")
        self.assertEqual(self.db.get("key1"), "val1")
        self.assertEqual(self.db.get("key2"), "val2")

    def test_bplus_tree_range_search(self):
        """Verify range queries traverse leaf pointers in sorted order."""
        self.db.put("a", "1")
        self.db.put("c", "3")
        self.db.put("b", "2")
        self.db.put("d", "4")
        
        # Scan a subset range
        results = self.db.get_range("b", "c")
        self.assertEqual(len(results), 2)
        self.assertEqual(results["b"], "2")
        self.assertEqual(results["c"], "3")
        self.assertNotIn("a", results)
        self.assertNotIn("d", results)

    def test_tombstone_deletion_bplus(self):
        """Verify deletions remove pointers correctly out of the B+ Tree leaf."""
        self.db.put("ghost", "data")
        self.db.delete("ghost")
        self.assertIsNone(self.db.get("ghost"))

    def test_compaction_with_bplus_tree(self):
        """Verify disk compaction reconstructs a pristine B+ Tree index map."""
        self.db.put("k1", "v1")
        self.db.put("k1", "v2")
        self.db.compact()
        self.assertEqual(self.db.get("k1"), "v2")

if __name__ == "__main__":
    unittest.main()