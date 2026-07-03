# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - Stable Production Release

### Added
- **Storage Layer:** Implemented fixed 4KB page allocation boundaries and virtual memory mapping (`mmap`).
- **Persistence:** Introduced an append-only Write-Ahead Log (`wal.log`) for atomic crash consistency and automated recovery.
- **Indexing:** Swapped standard dictionaries for a custom, self-balancing B+ Tree index with sequential leaf pointers supporting alphabetic range scans.
- **Maintenance:** Built an automated Tombstone delete tracker and background storage Compaction engine.
- **Safety:** Configured a fine-grained thread locking synchronization module and concurrency stress tests.
- **Automation:** Established GitHub Actions CI/CD pipeline verification rules.

### Fixed
- **B+ Tree Indexing:** Resolved a critical structural edge case bug during mid-node splits under non-sequential random insertion workloads.