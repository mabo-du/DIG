//! Sensors & Software .DT1/.HD format parser.
//!
//! Clean-room implementation based on the research paper
//! "Deconstructing Geophysical Data Formats". The DT1 format uses
//! interleaved 128-byte trace headers with per-trace spatial metadata.
//!
//! File structure:
//!   [trace_header_0 (128 bytes)] [trace_data_0 (N samples × B bytes)]
//!   [trace_header_1 (128 bytes)] [trace_data_1 ...]
//!
//! The .HD sidecar file provides survey-level metadata (samples per trace,
//! time window, channels, etc.) as ASCII key=value pairs.

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
}

/// Survey-level metadata parsed from .HD file.
#[derive(Debug, Clone, Default)]
pub struct HdMetadata {
    pub survey_name: String,
    pub num_traces: Option<usize>,
    pub samples_per_trace: usize,
    pub time_window_ns: f32,
    pub pull_delay_ns: f32,
    pub stacking: u32,
    pub transmit_rate_hz: f32,
    pub channels: u16,
    pub bits_per_sample: u8,
}

/// Parse a .HD ASCII header file and return survey metadata.
pub fn parse_hd(content: &str) -> HdMetadata {
    let mut meta = HdMetadata::default();

    for line in content.lines() {
        let line = line.trim();
        // Skip empty lines and comments
        if line.is_empty() || line.starts_with('#') || line.starts_with(';') {
            continue;
        }
        // Parse key=value (with optional spaces around =)
        if let Some(eq_pos) = line.find('=') {
            let key = line[..eq_pos].trim().to_uppercase();
            let val = line[eq_pos + 1..].trim();

            match key.as_str() {
                "SURVEYNAME" => meta.survey_name = val.to_string(),
                "NUMBEROFTRACES" => meta.num_traces = val.parse().ok(),
                "NUMBEROFPTS" | "NUMBEROFPOINTS" => {
                    if let Ok(n) = val.parse() {
                        meta.samples_per_trace = n;
                    }
                }
                "TIMEWINDOW" => {
                    if let Ok(t) = val.parse() {
                        meta.time_window_ns = t;
                    }
                }
                "PULLDELAY" => {
                    if let Ok(d) = val.parse() {
                        meta.pull_delay_ns = d;
                    }
                }
                "STACKING" => {
                    if let Ok(s) = val.parse() {
                        meta.stacking = s;
                    }
                }
                "TRANSMITRATE" => {
                    if let Ok(r) = val.parse() {
                        meta.transmit_rate_hz = r;
                    }
                }
                "NUMBEROFCHANNELS" => {
                    if let Ok(c) = val.parse() {
                        meta.channels = c;
                    }
                }
                "BITSPERSAMPLE" | "BITS_PER_SAMPLE" => {
                    if let Ok(b) = val.parse() {
                        meta.bits_per_sample = b;
                    }
                }
                _ => {}
            }
        }
    }

    // Apply defaults for unset fields
    if meta.samples_per_trace == 0 {
        meta.samples_per_trace = 512;
    }
    if meta.bits_per_sample == 0 {
        meta.bits_per_sample = 16;
    }
    if meta.channels == 0 {
        meta.channels = 1;
    }

    meta
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
        },
    ))
}

/// Parse a .DT1 file and return a PySurvey with trace data and per-trace metadata.
///
/// The .HD metadata provides samples_per_trace, bits_per_sample, etc.
/// If `hd_content` is None, defaults are used (512 samples, 16-bit).
pub fn parse_file(
    path: &str,
    hd_content: Option<&str>,
) -> Result<PySurvey, Box<dyn std::error::Error>> {
    let data = std::fs::read(path)?;
    if data.len() < 128 + 16 {
        return Err("File too small for DT1 format".into());
    }

    // Parse .HD metadata or use defaults
    let hd_meta = match hd_content {
        Some(content) => parse_hd(content),
        None => HdMetadata::default(),
    };

    let bytes_per_sample = (hd_meta.bits_per_sample / 8) as usize;
    let trace_header_size = 128usize;
    let trace_data_size = hd_meta.samples_per_trace * bytes_per_sample;
    let trace_total = trace_header_size + trace_data_size;

    // Scan through file, parsing trace headers and collecting data
    let mut offset = 0usize;
    let mut trace_headers: Vec<TraceHeader> = Vec::new();
    let mut trace_data: Vec<u8> = Vec::new();

    while offset + trace_total <= data.len() {
        match parse_trace_header(&data[offset..]) {
            Ok((_remaining, header)) => {
                let data_start = offset + trace_header_size;
                let data_end = data_start + trace_data_size;
                trace_data.extend_from_slice(&data[data_start..data_end]);
                trace_headers.push(header);
                offset += trace_total;
            }
            Err(_) => break,
        }
    }

    let num_traces = trace_headers.len();
    if num_traces == 0 {
        return Err("No valid traces found in DT1 file".into());
    }

    // Build survey
    let mut survey = PySurvey::new(path.to_string(), "dt1".to_string());
    survey.num_traces = num_traces;
    survey.samples_per_trace = hd_meta.samples_per_trace;
    survey.bits_per_sample = hd_meta.bits_per_sample;
    survey.channels = hd_meta.channels;
    survey.header_offset = 0; // Not applicable for DT1 (interleaved format)
    survey.sample_interval_ns = if hd_meta.samples_per_trace > 0 {
        hd_meta.time_window_ns / hd_meta.samples_per_trace as f32
    } else {
        0.0
    };
    survey.time_zero_ns = hd_meta.pull_delay_ns;
    survey.time_window_ns = hd_meta.time_window_ns;
    survey.trace_data = trace_data;
    survey.trace_positions = trace_headers.iter().map(|h| h.position).collect();
    survey.trace_time_zeros = trace_headers.iter().map(|h| h.time_zero).collect();
    survey.trace_elevations = trace_headers.iter().map(|h| h.elevation).collect();

    Ok(survey)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── .HD parser tests ──────────────────────────────────────────────

    fn sample_hd() -> &'static str {
        "\
SURVEYNAME = Test Survey
NUMBEROFTRACES = 50
NUMBEROFPTS = 256
TIMEWINDOW = 80
PULLDELAY = 1.5
STACKING = 4
TRANSMITRATE = 100
NUMBEROFCHANNELS = 1
"
    }

    #[test]
    fn test_parse_hd_full() {
        let meta = parse_hd(sample_hd());
        assert_eq!(meta.survey_name, "Test Survey");
        assert_eq!(meta.num_traces, Some(50));
        assert_eq!(meta.samples_per_trace, 256);
        assert!((meta.time_window_ns - 80.0).abs() < 0.01);
        assert!((meta.pull_delay_ns - 1.5).abs() < 0.01);
        assert_eq!(meta.stacking, 4);
        assert!((meta.transmit_rate_hz - 100.0).abs() < 0.01);
        assert_eq!(meta.channels, 1);
        assert_eq!(meta.bits_per_sample, 16); // default
    }

    #[test]
    fn test_parse_hd_empty() {
        let meta = parse_hd("");
        assert_eq!(meta.samples_per_trace, 512); // default
        assert_eq!(meta.bits_per_sample, 16); // default
        assert_eq!(meta.channels, 1); // default
    }

    #[test]
    fn test_parse_hd_case_insensitive() {
        let content = "numberofpts = 128\nbitspersample = 8\n";
        let meta = parse_hd(content);
        assert_eq!(meta.samples_per_trace, 128);
        assert_eq!(meta.bits_per_sample, 8);
    }

    #[test]
    fn test_parse_hd_with_comments() {
        let content = "# This is a comment\nNUMBEROFPTS = 512\n; Also a comment\nTIMEWINDOW = 100\n";
        let meta = parse_hd(content);
        assert_eq!(meta.samples_per_trace, 512);
        assert!((meta.time_window_ns - 100.0).abs() < 0.01);
    }

    #[test]
    fn test_parse_hd_alternative_keys() {
        let content = "NUMBEROFPOINTS = 1024\nBITS_PER_SAMPLE = 32\n";
        let meta = parse_hd(content);
        assert_eq!(meta.samples_per_trace, 1024);
        assert_eq!(meta.bits_per_sample, 32);
    }

    // ── Trace header tests ────────────────────────────────────────────

    fn make_trace_header(
        trace_number: i32,
        position: f32,
        time_zero: f32,
        elevation: f32,
        fiducial: u8,
    ) -> Vec<u8> {
        let mut buf = vec![0u8; 128];
        buf[0..4].copy_from_slice(&trace_number.to_le_bytes());
        buf[8..12].copy_from_slice(&position.to_le_bytes());
        buf[16..20].copy_from_slice(&time_zero.to_le_bytes());
        buf[20..24].copy_from_slice(&elevation.to_le_bytes());
        if fiducial != 0 {
            buf[100] = fiducial; // first char byte
        }
        buf
    }

    #[test]
    fn test_parse_trace_header_basic() {
        let buf = make_trace_header(1, 10.5, 2.0, 45.0, 0);
        let (_rest, header) = parse_trace_header(&buf).unwrap();
        assert_eq!(header.trace_number, 1);
        assert!((header.position - 10.5).abs() < 0.01);
        assert!((header.time_zero - 2.0).abs() < 0.01);
        assert!((header.elevation - 45.0).abs() < 0.01);
        assert_eq!(header.fiducial, 0);
    }

    #[test]
    fn test_parse_trace_header_fiducial() {
        let buf = make_trace_header(5, 20.0, 1.0, 100.0, b'M');
        let (_rest, header) = parse_trace_header(&buf).unwrap();
        assert_eq!(header.trace_number, 5);
        assert_eq!(header.fiducial, b'M');
    }

    #[test]
    fn test_parse_trace_header_negative_position() {
        let buf = make_trace_header(1, -5.0, 0.0, 0.0, 0);
        let (_rest, header) = parse_trace_header(&buf).unwrap();
        assert!((header.position - (-5.0)).abs() < 0.01);
    }

    // ── File parsing tests ────────────────────────────────────────────

    /// Build a synthetic DT1 file with trace headers + data.
    fn make_synthetic_dt1(
        num_traces: usize,
        samples: usize,
        bits: u8,
    ) -> Vec<u8> {
        let bytes_per_sample = (bits / 8) as usize;
        let trace_data_size = samples * bytes_per_sample;
        let trace_total = 128 + trace_data_size;
        let mut buf = vec![0u8; num_traces * trace_total];

        for t in 0..num_traces {
            let offset = t * trace_total;
            // Write trace header
            buf[offset..offset + 4].copy_from_slice(&(t as i32 + 1).to_le_bytes());
            buf[offset + 8..offset + 12].copy_from_slice(&(t as f32 * 2.0).to_le_bytes()); // position
            buf[offset + 16..offset + 20].copy_from_slice(&1.0f32.to_le_bytes()); // time_zero
            buf[offset + 20..offset + 24].copy_from_slice(&(t as f32 * 5.0).to_le_bytes()); // elevation

            // Write trace data with recognizable pattern
            let data_start = offset + 128;
            for s in 0..samples {
                let sample_offset = data_start + s * bytes_per_sample;
                if bits == 16 {
                    let val = ((t * 100 + s) & 0xFFFF) as i16;
                    buf[sample_offset..sample_offset + 2].copy_from_slice(&val.to_le_bytes());
                } else if bits == 8 {
                    buf[sample_offset] = ((t + s) & 0xFF) as u8;
                } else if bits == 32 {
                    let val = ((t * 1000 + s) & 0xFFFFFFFF) as i32;
                    buf[sample_offset..sample_offset + 4].copy_from_slice(&val.to_le_bytes());
                }
            }
        }
        buf
    }

    #[test]
    fn test_parse_file_basic() {
        let dt1 = make_synthetic_dt1(10, 256, 16);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dt1");
        std::fs::write(&path, &dt1).unwrap();

        let survey = parse_file(path.to_str().unwrap(), Some(sample_hd())).unwrap();
        assert_eq!(survey.num_traces, 10);
        assert_eq!(survey.samples_per_trace, 256);
        assert_eq!(survey.bits_per_sample, 16);
        assert_eq!(survey.channels, 1);
        assert!((survey.time_window_ns - 80.0).abs() < 0.01);
        assert!((survey.time_zero_ns - 1.5).abs() < 0.01);
    }

    #[test]
    fn test_parse_file_trace_data_values() {
        let dt1 = make_synthetic_dt1(5, 64, 16);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dt1");
        std::fs::write(&path, &dt1).unwrap();

        let hd = "NUMBEROFPTS = 64\n";
        let survey = parse_file(path.to_str().unwrap(), Some(hd)).unwrap();
        assert_eq!(survey.num_traces, 5);
        assert_eq!(survey.samples_per_trace, 64);

        // Check trace data was extracted
        assert!(!survey.trace_data.is_empty());
        // 5 traces × 64 samples × 2 bytes = 640 bytes
        assert_eq!(survey.trace_data.len(), 5 * 64 * 2);
    }

    #[test]
    fn test_parse_file_with_hd_samples() {
        let dt1 = make_synthetic_dt1(8, 128, 16);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dt1");
        std::fs::write(&path, &dt1).unwrap();

        let hd = "NUMBEROFPTS = 128\nTIMEWINDOW = 50\n";
        let survey = parse_file(path.to_str().unwrap(), Some(hd)).unwrap();
        assert_eq!(survey.num_traces, 8);
        assert_eq!(survey.samples_per_trace, 128);
        assert!((survey.time_window_ns - 50.0).abs() < 0.01);
        assert_eq!(survey.trace_data.len(), 8 * 128 * 2);
    }

    #[test]
    fn test_parse_file_per_trace_metadata() {
        let dt1 = make_synthetic_dt1(4, 32, 16);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dt1");
        std::fs::write(&path, &dt1).unwrap();

        let hd = "NUMBEROFPTS = 32\n";
        let survey = parse_file(path.to_str().unwrap(), Some(hd)).unwrap();
        assert_eq!(survey.trace_positions.len(), 4);
        assert_eq!(survey.trace_time_zeros.len(), 4);
        assert_eq!(survey.trace_elevations.len(), 4);

        // Trace 0: position=0.0, time_zero=1.0, elevation=0.0
        assert!((survey.trace_positions[0] - 0.0).abs() < 0.01);
        assert!((survey.trace_time_zeros[0] - 1.0).abs() < 0.01);
        assert!((survey.trace_elevations[0] - 0.0).abs() < 0.01);

        // Trace 1: position=2.0, time_zero=1.0, elevation=5.0
        assert!((survey.trace_positions[1] - 2.0).abs() < 0.01);
        assert!((survey.trace_elevations[1] - 5.0).abs() < 0.01);
    }

    #[test]
    fn test_parse_file_8bit() {
        let dt1 = make_synthetic_dt1(3, 64, 8);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_8bit.dt1");
        std::fs::write(&path, &dt1).unwrap();

        let hd = "NUMBEROFPTS = 64\nBITSPERSAMPLE = 8\n";
        let survey = parse_file(path.to_str().unwrap(), Some(hd)).unwrap();
        assert_eq!(survey.num_traces, 3);
        assert_eq!(survey.samples_per_trace, 64);
        assert_eq!(survey.bits_per_sample, 8);
        assert_eq!(survey.trace_data.len(), 3 * 64 * 1);
    }

    #[test]
    fn test_parse_file_32bit() {
        let dt1 = make_synthetic_dt1(2, 32, 32);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_32bit.dt1");
        std::fs::write(&path, &dt1).unwrap();

        let hd = "NUMBEROFPTS = 32\nBITS_PER_SAMPLE = 32\n";
        let survey = parse_file(path.to_str().unwrap(), Some(hd)).unwrap();
        assert_eq!(survey.num_traces, 2);
        assert_eq!(survey.samples_per_trace, 32);
        assert_eq!(survey.bits_per_sample, 32);
        assert_eq!(survey.trace_data.len(), 2 * 32 * 4);
    }

    #[test]
    fn test_parse_file_missing_file() {
        let result = parse_file("/nonexistent/file.dt1", None);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_file_too_small() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("tiny.dt1");
        std::fs::write(&path, &[0u8; 10]).unwrap();

        let result = parse_file(path.to_str().unwrap(), None);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_file_no_valid_traces() {
        // File with header but not enough data for even one full trace
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("invalid.dt1");
        let mut buf = vec![0u8; 128 + 10]; // header + 10 bytes (need 128+512*2=1152 for default)
        buf[0..4].copy_from_slice(&1i32.to_le_bytes());
        std::fs::write(&path, &buf).unwrap();

        let result = parse_file(path.to_str().unwrap(), None);
        assert!(result.is_err());
    }
}