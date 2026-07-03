# Low-Level On-Disk Disk Storage Format

The physical database file structure utilizes strict byte serialization protocols to represent active and dead states on raw storage media.

## Layout Configuration
The storage architecture adheres to a fixed hardware page boundary sizing constraint:
* **Page Unit Sizing:** 4,096 bytes (4KB structural blocks)

## Data Payload Record Packing Structure
Records are appended sequentially within allocated hardware block frames using big-endian serialization format (`>BHI` protocol):

| Segment | Length | Variable DataType | Description |
| :--- | :--- | :--- | :--- |
| **Record Type** | 1 Byte | `unsigned char` | Status flag (`0x00` = Active Write, `0x01` = Tombstone Deletion) |
| **Key Length** | 2 Bytes | `unsigned short` | Declares variable boundary length of target Key string |
| **Value Length**| 4 Bytes | `unsigned int` | Declares variable boundary length of target Value string |
| **Key Byte Array**| N Bytes | `char[]` | Raw UTF-8 encoded string array representing database identifier key |
| **Val Byte Array**| M Bytes | `char[]` | Raw UTF-8 encoded payload data (omitted entirely during Deletions) |