//! Memory-mapped I/O for out-of-core data access.
//!
//! Raw binary data is never fully loaded into Python's memory space.
//! Instead, it is memory-mapped via Rust's memmap2 and remains
//! strictly immutable on disk. Processing steps append operations to
//! the DAG rather than modifying the array.

pub mod memmap;