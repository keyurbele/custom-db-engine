# Architectural Trade-Off Analysis & Engineering Decisions

Building a system requires managing opposing technical goals. Below are the key trade-offs considered during development:

## 1. Hash Mapping Index vs. Balanced B+ Tree Structures
* *Hash Map:* $O(1)$ constant time lookup performance but lacks alphabetical grouping support.
* *B+ Tree (Selected):* Sacrifices lookup speed to $O(\log n)$ to unlock high-speed structural range scanning via sequential leaf nodes.

## 2. In-Place File Rewrites vs. Log-Structured Tombstone Deletions
* *In-Place:* Minimizes disk space growth but demands random seek lookups that create I/O bottlenecks.
* *Log-Structured (Selected):* Accelerates execution cycles by converting deletions into fast append writes, delegating space cleanup to an isolated background Compaction engine.