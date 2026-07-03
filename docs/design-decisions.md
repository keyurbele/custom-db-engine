## 📊 Core Operation Time Complexity ($O$ Notation)

The engine's operations balance in-memory speed with physical disk storage overhead:

* **`put(key, value)` — Time Complexity: $O(\log n)$**
  * *Why:* Writing the data payload onto the memory map and appending to the `wal.log` are immediate sequential append operations ($O(1)$). However, inserting the key tracking reference into our balanced B+ Tree requires climbing down structural node paths, which takes logarithmic time.
* **`get(key)` — Time Complexity: $O(1)$ (Cache Hit) / $O(\log n)$ (Cache Miss)**
  * *Why:* If the key resides in our volatile LRU memory cache, lookup is instantaneous. On a cache miss, the engine performs a logarithmic search through the internal B+ Tree index pointers to locate the physical page offset inside the memory-mapped storage file.
* **`get_range(start_key, end_key)` — Time Complexity: $O(\log n + k)$**
  * *Why:* The engine takes $O(\log n)$ time to locate the initial starting key node at the leaf layer of the B+ Tree. From there, it bypasses the rest of the tree and walks directly along the connected leaf sequence pointers to retrieve the next $k$ adjacent items sequentially.
* **`delete(key)` — Time Complexity: $O(\log n)$**
  * *Why:* Deletions follow our log-structured append policy. The engine quickly appends a 1-byte tombstone record onto the end of the data file and removes the target entry from the B+ Tree index space.