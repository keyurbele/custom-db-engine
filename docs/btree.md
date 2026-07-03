# Custom Self-Balancing B+ Tree Memory Index

The primary internal search index uses a custom, multi-degree self-balancing B+ Tree optimized for low-latency alphabetic scanning.

## Algorithmic Complexity

* **Point Lookup Resolution:** $O(\log n)$ via deep structural tree parent-to-child pointer hops.
* **Range Scans:** $O(k)$ where $k$ represents elements found between bounds.

## Structural Partitioning & Split Mechanics
Nodes maintain structural node degree constraints (Max Keys = 3). When keys exceed boundary limits, the node breaks symmetrically down the center point:
* **Leaf Splits:** Split elements mirror onto the left boundary edge of the right-hand child, and sequence references link leaf nodes together via leaf-level sequence pointers.
* **Internal Node Splits:** The middle split element extracts entirely out of the child array layer, pushing upward into the parent index key vector frame.