//! Sensors & Software .DT1/.HD format parser.
//!
//! Clean-room implementation based on the research paper
//! "Deconstructing Geophysical Data Formats". The DT1 format uses
//! interleaved 128-byte trace headers with per-trace spatial metadata.
//!
//! Each trace is preceded by a 128-byte header containing:
//!   - 25 × 4-byte fields (position, time-zero, elevation, etc.)
//!   - 28 × 1-byte characters (markers, flags)

use crate::types::survey::PySurvey;
use nom::{
    number::complete::{le_f32, le_i32},
    IResult,
};

/// Per-trace header (128 bytes).
#[derive(Debug, Clone)]
pub struct TraceHeader {
    pub trace_number: i32,
    pub position: f32,       // odometer position (m)
    pub time_zero: f32,      // time-zero offset (ns)
    pub elevation: f32,      // GPS elevation (m)
    pub fiducial: u8,        // fiducial marker flag
    pub samples: i32,        // samples in this trace
}

/// Parse a single 128-byte trace header.
pub fn parse_trace_header(input: &[u8]) -> IResult<&[u8], TraceHeader> {
    let (input, trace_number) = le_i32(input)?;
    let (input, _reserved1) = le_i32(input)?;
    let (input, position) = le_f32(input)?;
    let (input, _reserved2) = le_f32(input)?;
    let (input, time_zero) = le_f32(input)?;
    let (input, elevation) = le_f32(input)?;
    // Skip remaining 4-byte fields (bytes 24-100)
    let (input, _) = nom::bytes::complete::take(76usize)(input)?;
    // Read 28 character bytes
    let (input, chars) = nom::bytes::complete::take(28usize)(input)?;
    let fiducial = chars.first().copied().unwrap_or(0);

    Ok((
        input,
        TraceHeader {
            trace_number,
            position,
            time_zero,
            elevation,
            fiducial,
            samples: 0, // populated from .HD file
        },
    ))
}

/// Parse a .DT1 file and return a PySurvey.
pub fn parse_file(path: &str) -> Result<PySurvey, Box<dyn std::error::Error>> {
    let data = std::fs::read(path)?;
    if data.len() < 128 + 16 {
        return Err("File too small for DT1 format".into());
    }
    let mut survey = PySurvey::new(path.to_string(), "dt1".to_string());

    // Count traces by scanning 128-byte headers
    let trace_header_size = 128usize;
    let mut offset = 0;
    let mut trace_count = 0;

    while offset + trace_header_size + 16 <= data.len() {
        match parse_trace_header(&data[offset..]) {
            Ok((_remaining, _header)) => {
                // Trace header is always 128 bytes
                let trace_data_size = 512 * 2; // 512 samples × 2 bytes (default)
                let trace_total = trace_header_size + trace_data_size;
                if offset + trace_total > data.len() {
                    break;
                }
                offset += trace_total;
                trace_count += 1;
            }
            Err(_) => break,
        }
    }

    survey.num_traces = trace_count;
    survey.samples_per_trace = 512; // default, refined from .HD
    survey.bits_per_sample = 16;
    survey.format = "dt1".to_string();

    Ok(survey)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_trace_header() {
        let mut buf = vec![0u8; 128];
        // trace_number = 1
        buf[0..4].copy_from_slice(&1i32.to_le_bytes());
        // position = 10.5 m
        buf[8..12].copy_from_slice(&10.5f32.to_le_bytes());
        // time_zero = 2.0 ns
        buf[16..20].copy_from_slice(&2.0f32.to_le_bytes());
        // elevation = 45.0 m
        buf[20..24].copy_from_slice(&45.0f32.to_le_bytes());

        let (_rest, header) = parse_trace_header(&buf).unwrap();
        assert_eq!(header.trace_number, 1);
        assert!((header.position - 10.5).abs() < 0.01);
        assert!((header.time_zero - 2.0).abs() < 0.01);
        assert!((header.elevation - 45.0).abs() < 0.01);
    }
}