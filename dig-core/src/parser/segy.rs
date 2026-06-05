//! SEG-Y format parser (stub).
//!
//! SEG-Y is the Society of Exploration Geophysicists interchange format.
//! Structure:
//!   - 3200-byte EBCDIC text header
//!   - 400-byte binary file header
//!   - Per-trace: 240-byte trace header + trace data

use crate::types::survey::PySurvey;

/// Parse a SEG-Y file and return a PySurvey.
pub fn parse_file(path: &str) -> Result<PySurvey, Box<dyn std::error::Error>> {
    let data = std::fs::read(path)?;
    if data.len() < 3600 {
        return Err("File too small for SEG-Y header".into());
    }

    // Parse 400-byte binary header at offset 3200
    let _sample_format = i16::from_be_bytes([data[3221], data[3220]]); // bytes 3221-3220
    let _samples_per_trace =
        u16::from_be_bytes([data[3225], data[3224]]) as usize; // bytes 3225-3224

    let mut survey = PySurvey::new(path.to_string(), "segy".to_string());
    survey.format = "segy".to_string();
    survey.bits_per_sample = 32; // IBM float / IEEE float

    Ok(survey)
}