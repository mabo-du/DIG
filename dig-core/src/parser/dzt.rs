//! GSSI .DZT format parser.
//!
//! Based on the readgssi byte-offset specification (MIT-compatible
//! pattern adaptation). The DZT format is a proprietary binary format
//! used by GSSI SIR-3000/4000 control units.
//!
//! Header layout (from research paper):
//!   Offset | Type   | Field
//!   -------|--------|-------------------------------
//!   00     | int16  | rh_tag (header tag)
//!   02     | int16  | rh_data (header size multiplier)
//!   04     | int16  | rh_nsamp (samples per trace)
//!   06     | int16  | rh_bits (bits per sample)
//!   08     | int16  | rh_zero (binary offset)
//!   10     | float32| rhf_sps (scans per second)
//!   14     | float32| rhf_spm (scans per meter)
//!   18     | float32| rhf_mpm (meters per marker)
//!   22     | float32| rhf_position (start position, ns)
//!   26     | float32| rhf_range (time window, ns)
//!   52     | int16  | rh_nchan (number of channels)

use crate::types::survey::PySurvey;
use nom::{
    number::complete::{le_f32, le_i16},
    IResult,
};

/// Parsed DZT header fields.
#[derive(Debug, Clone)]
pub struct DztHeader {
    pub rh_tag: i16,
    pub rh_data: i16,
    pub rh_nsamp: i16,
    pub rh_bits: i16,
    pub rh_zero: i16,
    pub rhf_sps: f32,
    pub rhf_spm: f32,
    pub rhf_mpm: f32,
    pub rhf_position: f32,
    pub rhf_range: f32,
    pub rh_nchan: i16,
}

/// Parse the 1024+ byte DZT header from raw bytes.
pub fn parse_header(input: &[u8]) -> IResult<&[u8], DztHeader> {
    let (input, rh_tag) = le_i16(input)?;
    let (input, rh_data) = le_i16(input)?;
    let (input, rh_nsamp) = le_i16(input)?;
    let (input, rh_bits) = le_i16(input)?;
    let (input, rh_zero) = le_i16(input)?;
    let (input, rhf_sps) = le_f32(input)?;
    let (input, rhf_spm) = le_f32(input)?;
    let (input, rhf_mpm) = le_f32(input)?;
    let (input, rhf_position) = le_f32(input)?;
    let (input, rhf_range) = le_f32(input)?;
    // Skip bytes 30-51 (reserved)
    let (input, _) = nom::bytes::complete::take(22usize)(input)?;
    let (input, rh_nchan) = le_i16(input)?;

    Ok((
        input,
        DztHeader {
            rh_tag,
            rh_data,
            rh_nsamp,
            rh_bits,
            rh_zero,
            rhf_sps,
            rhf_spm,
            rhf_mpm,
            rhf_position,
            rhf_range,
            rh_nchan,
        },
    ))
}

/// Calculate the total header byte offset.
///
/// From the research paper:
///   If rh_data < 1024: offset = rh_data * rh_nsamp
///   Otherwise:         offset = rh_data * rh_nchan
pub fn header_offset(header: &DztHeader) -> usize {
    if header.rh_data < 1024 {
        (header.rh_data as usize) * (header.rh_nsamp as usize)
    } else {
        (header.rh_data as usize) * (header.rh_nchan as usize)
    }
    .max(1024) // minimum header size
}

/// Parse a .DZT file and return a PySurvey.
pub fn parse_file(path: &str) -> Result<PySurvey, Box<dyn std::error::Error>> {
    let data = std::fs::read(path)?;
    let (_rest, header) = parse_header(&data)
        .map_err(|e| format!("Failed to parse DZT header: {:?}", e))?;

    let hdr_offset = header_offset(&header);
    let bytes_per_sample = (header.rh_bits / 8) as usize;
    let trace_bytes = (header.rh_nsamp as usize) * bytes_per_sample;
    let num_traces = (data.len() - hdr_offset) / trace_bytes;

    let mut survey = PySurvey::new(path.to_string(), "dzt".to_string());
    survey.num_traces = num_traces;
    survey.samples_per_trace = header.rh_nsamp as usize;
    survey.bits_per_sample = header.rh_bits as u8;
    survey.sample_interval_ns = header.rhf_range / header.rh_nsamp as f32;
    survey.traces_per_second = header.rhf_sps;
    survey.traces_per_meter = header.rhf_spm;
    survey.time_zero_ns = header.rhf_position;
    survey.time_window_ns = header.rhf_range;
    survey.channels = header.rh_nchan as u16;

    Ok(survey)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Minimal synthetic DZT header (1024 bytes of zeros with known fields).
    fn make_synthetic_dzt() -> Vec<u8> {
        let mut buf = vec![0u8; 1024];
        // rh_tag = 1
        buf[0..2].copy_from_slice(&1i16.to_le_bytes());
        // rh_data = 1024 (header size)
        buf[2..4].copy_from_slice(&1024i16.to_le_bytes());
        // rh_nsamp = 512
        buf[4..6].copy_from_slice(&512i16.to_le_bytes());
        // rh_bits = 16
        buf[6..8].copy_from_slice(&16i16.to_le_bytes());
        // rhf_range = 100.0 ns
        buf[26..30].copy_from_slice(&100.0f32.to_le_bytes());
        // rh_nchan = 1
        buf[52..54].copy_from_slice(&1i16.to_le_bytes());
        buf
    }

    #[test]
    fn test_parse_dzt_header() {
        let buf = make_synthetic_dzt();
        let (_rest, header) = parse_header(&buf).unwrap();
        assert_eq!(header.rh_tag, 1);
        assert_eq!(header.rh_nsamp, 512);
        assert_eq!(header.rh_bits, 16);
        assert!((header.rhf_range - 100.0).abs() < 0.01);
        assert_eq!(header.rh_nchan, 1);
    }

    #[test]
    fn test_header_offset_minimum() {
        let buf = make_synthetic_dzt();
        let (_rest, header) = parse_header(&buf).unwrap();
        let offset = header_offset(&header);
        assert!(offset >= 1024);
    }
}