//! Memory-mapped file abstraction for out-of-core GPR data.
//!
//! Maps raw binary files into virtual memory so the OS handles
//! paging. Only the traces actually accessed are loaded into RAM.

use memmap2::Mmap;

/// A memory-mapped view of a binary geophysical data file.
///
/// The underlying file is never fully loaded into RAM. The OS
/// pages in only the regions that are actually read.
#[derive(Debug)]
pub struct MemmapFile {
    pub path: String,
    pub mmap: Mmap,
    pub file_size: usize,
}

impl MemmapFile {
    /// Open and memory-map a file.
    pub fn open(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let file = std::fs::File::open(path)?;
        let file_size = file.metadata()?.len() as usize;
        let mmap = unsafe { Mmap::map(&file)? };
        Ok(MemmapFile {
            path: path.to_string(),
            mmap,
            file_size,
        })
    }

    /// Read a slice of bytes from the memory-mapped region.
    pub fn read_slice(&self, offset: usize, length: usize) -> &[u8] {
        let end = (offset + length).min(self.file_size);
        &self.mmap[offset..end]
    }

    /// Read a single trace from a DZT file.
    ///
    /// Returns the raw bytes for trace `index`, given the header
    /// offset and trace byte size.
    pub fn read_trace_dzt(&self, index: usize, header_offset: usize, trace_bytes: usize) -> &[u8] {
        let offset = header_offset + index * trace_bytes;
        self.read_slice(offset, trace_bytes)
    }

    /// Read a single trace from a DT1 file (with 128-byte trace header).
    pub fn read_trace_dt1(&self, index: usize, trace_data_bytes: usize) -> &[u8] {
        let trace_total = 128 + trace_data_bytes; // header + data
        let offset = index * trace_total + 128; // skip header
        self.read_slice(offset, trace_data_bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_memmap_open() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.bin");
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(&[0u8; 4096]).unwrap();

        let mmap = MemmapFile::open(path.to_str().unwrap()).unwrap();
        assert_eq!(mmap.file_size, 4096);
    }

    #[test]
    fn test_read_slice() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.bin");
        let mut f = std::fs::File::create(&path).unwrap();
        let data: Vec<u8> = (0..100).collect();
        f.write_all(&data).unwrap();

        let mmap = MemmapFile::open(path.to_str().unwrap()).unwrap();
        let slice = mmap.read_slice(10, 5);
        assert_eq!(slice, &[10, 11, 12, 13, 14]);
    }
}