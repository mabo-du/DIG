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
/// From the readgssi specification:
///   If rh_data < 1024: offset = rh_data * rh_nsamp (rh_data is a multiplier)
///   If rh_data >= 1024: offset = rh_data (rh_data IS the header size in bytes)
pub fn header_offset(header: &DztHeader) -> usize {
    let offset = if header.rh_data < 1024 {
        (header.rh_data as usize) * (header.rh_nsamp as usize)
    } else {
        header.rh_data as usize
    };
    offset.max(1024) // minimum header size
}

/// Parse a .DZT file and return a PySurvey with header metadata.
///
/// Trace data is NOT loaded into memory — the caller memory-maps the raw
/// file using `header_offset`, `num_traces`, `samples_per_trace`, and
/// `bits_per_sample` to interpret the binary trace array.
pub fn parse_file(path: &str) -> Result<PySurvey, Box<dyn std::error::Error>> {
    let data = std::fs::read(path)?;
    let (_rest, header) = parse_header(&data)
        .map_err(|e| format!("Failed to parse DZT header: {:?}", e))?;

    let hdr_offset = header_offset(&header);
    let bytes_per_sample = (header.rh_bits / 8) as usize;
    // Each trace record contains nsamp samples per channel, interleaved
    let trace_record_bytes = (header.rh_nsamp as usize)
        * bytes_per_sample
        * (header.rh_nchan as usize);
    let num_traces = if trace_record_bytes > 0 {
        (data.len() - hdr_offset) / trace_record_bytes
    } else {
        0
    };

    let mut survey = PySurvey::new(path.to_string(), "dzt".to_string());
    survey.num_traces = num_traces;
    survey.samples_per_trace = header.rh_nsamp as usize;
    survey.bits_per_sample = header.rh_bits as u8;
    survey.header_offset = hdr_offset;
    survey.sample_interval_ns = header.rhf_range / header.rh_nsamp as f32;
    survey.traces_per_second = header.rhf_sps;
    survey.traces_per_meter = header.rhf_spm;
    survey.time_zero_ns = header.rhf_position;
    survey.time_window_ns = header.rhf_range;
    survey.channels = header.rh_nchan as u16;

    Ok(survey)
}

/// Parse a .DZG sidecar GPS file (NMEA sentences, one per trace).
///
/// Returns a Vec of (trace_index, latitude, longitude, elevation) tuples.
/// Each line should be a $GPGGA or $GPRMC NMEA sentence corresponding
/// to the trace at that index.
pub fn parse_dzg(path: &str) -> Result<Vec<(usize, f64, f64, f64)>, Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(path)?;
    let mut positions: Vec<(usize, f64, f64, f64)> = Vec::new();

    for (i, line) in content.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Some(pos) = parse_nmea_gpgga(line) {
            positions.push((i, pos.0, pos.1, pos.2));
        } else if let Some(pos) = parse_nmea_gprmc(line) {
            positions.push((i, pos.0, pos.1, 0.0));
        }
    }

    Ok(positions)
}

/// Parse a $GPGGA NMEA sentence.
/// Returns (latitude, longitude, elevation_altitude).
fn parse_nmea_gpgga(sentence: &str) -> Option<(f64, f64, f64)> {
    let parts: Vec<&str> = sentence.split(',').collect();
    if parts.len() < 10 || parts[0] != "$GPGGA" {
        return None;
    }

    let lat = parse_nmea_coordinate(parts[2], parts[3])?;
    let lon = parse_nmea_coordinate(parts[4], parts[5])?;
    let alt: f64 = parts[9].parse().ok()?;

    Some((lat, lon, alt))
}

/// Parse a $GPRMC NMEA sentence.
/// Returns (latitude, longitude, 0.0) — no altitude in RMC.
fn parse_nmea_gprmc(sentence: &str) -> Option<(f64, f64, f64)> {
    let parts: Vec<&str> = sentence.split(',').collect();
    if parts.len() < 8 || parts[0] != "$GPRMC" {
        return None;
    }

    let lat = parse_nmea_coordinate(parts[3], parts[4])?;
    let lon = parse_nmea_coordinate(parts[5], parts[6])?;

    Some((lat, lon, 0.0))
}

/// Parse an NMEA coordinate (DDDMM.MMMM or DDMM.MMMM format).
fn parse_nmea_coordinate(value: &str, hemisphere: &str) -> Option<f64> {
    if value.is_empty() || hemisphere.is_empty() {
        return None;
    }

    let decimal = value.parse::<f64>().ok()?;

    // Determine degrees digits: 3 for longitude (DDD), 2 for latitude (DD)
    let deg = (decimal / 100.0).floor();
    let min = decimal - deg * 100.0;

    let mut coord = deg + min / 60.0;
    if hemisphere == "S" || hemisphere == "W" {
        coord = -coord;
    }

    Some(coord)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    /// Minimal synthetic DZT header (1024 bytes of zeros with known fields).
    fn make_synthetic_dzt_header() -> Vec<u8> {
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
        // rhf_sps = 50.0
        buf[10..14].copy_from_slice(&50.0f32.to_le_bytes());
        // rhf_spm = 10.0
        buf[14..18].copy_from_slice(&10.0f32.to_le_bytes());
        // rhf_position = 2.0 ns (time-zero)
        buf[22..26].copy_from_slice(&2.0f32.to_le_bytes());
        // rh_nchan = 1
        buf[52..54].copy_from_slice(&1i16.to_le_bytes());
        buf
    }

    /// Create a complete synthetic DZT file with header + trace data.
    fn make_synthetic_dzt_file(
        nsamp: i16,
        bits: i16,
        nchan: i16,
        num_traces: usize,
    ) -> Vec<u8> {
        let mut buf = make_synthetic_dzt_header();
        // Override with custom values
        buf[4..6].copy_from_slice(&nsamp.to_le_bytes());
        buf[6..8].copy_from_slice(&bits.to_le_bytes());
        buf[52..54].copy_from_slice(&nchan.to_le_bytes());

        let bytes_per_sample = (bits / 8) as usize;
        let trace_bytes = (nsamp as usize) * bytes_per_sample * (nchan as usize);
        let total_trace_data = num_traces * trace_bytes;
        let mut trace_data = vec![0u8; total_trace_data];

        // Fill with recognizable pattern: each trace = trace_index
        for t in 0..num_traces {
            let offset = t * trace_bytes;
            let val = (t % 256) as u8;
            // Set first byte of each sample to a trace-specific value
            for s in 0..(nsamp as usize) {
                let sample_offset = offset + s * bytes_per_sample;
                if sample_offset < total_trace_data {
                    trace_data[sample_offset] = val;
                }
            }
        }

        buf.extend_from_slice(&trace_data);
        buf
    }

    #[test]
    fn test_parse_dzt_header() {
        let buf = make_synthetic_dzt_header();
        let (_rest, header) = parse_header(&buf).unwrap();
        assert_eq!(header.rh_tag, 1);
        assert_eq!(header.rh_nsamp, 512);
        assert_eq!(header.rh_bits, 16);
        assert!((header.rhf_range - 100.0).abs() < 0.01);
        assert!((header.rhf_sps - 50.0).abs() < 0.01);
        assert!((header.rhf_spm - 10.0).abs() < 0.01);
        assert!((header.rhf_position - 2.0).abs() < 0.01);
        assert_eq!(header.rh_nchan, 1);
    }

    #[test]
    fn test_header_offset_minimum() {
        let buf = make_synthetic_dzt_header();
        let (_rest, header) = parse_header(&buf).unwrap();
        let offset = header_offset(&header);
        assert!(offset >= 1024);
    }

    #[test]
    fn test_header_offset_rh_data_override() {
        let mut buf = make_synthetic_dzt_header();
        // rh_data = 2048 (larger header, rh_data IS the byte count)
        buf[2..4].copy_from_slice(&2048i16.to_le_bytes());
        let (_rest, header) = parse_header(&buf).unwrap();
        let offset = header_offset(&header);
        // rh_data >= 1024, so offset = rh_data = 2048
        assert_eq!(offset, 2048);
    }

    #[test]
    fn test_header_offset_rh_data_multiplier() {
        let mut buf = make_synthetic_dzt_header();
        // rh_data = 4 (multiplier mode: offset = 4 * rh_nsamp = 4 * 512 = 2048)
        buf[2..4].copy_from_slice(&4i16.to_le_bytes());
        let (_rest, header) = parse_header(&buf).unwrap();
        let offset = header_offset(&header);
        assert_eq!(offset, 2048);
    }

    #[test]
    fn test_parse_file_16bit() {
        let dzt = make_synthetic_dzt_file(512, 16, 1, 100);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dzt");
        std::fs::write(&path, &dzt).unwrap();

        let survey = parse_file(path.to_str().unwrap()).unwrap();
        assert_eq!(survey.num_traces, 100);
        assert_eq!(survey.samples_per_trace, 512);
        assert_eq!(survey.bits_per_sample, 16);
        assert_eq!(survey.channels, 1);
        assert_eq!(survey.header_offset, 1024);
        assert!((survey.sample_interval_ns - 100.0 / 512.0).abs() < 0.001);
    }

    #[test]
    fn test_parse_file_8bit() {
        let dzt = make_synthetic_dzt_file(256, 8, 1, 50);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_8bit.dzt");
        std::fs::write(&path, &dzt).unwrap();

        let survey = parse_file(path.to_str().unwrap()).unwrap();
        assert_eq!(survey.num_traces, 50);
        assert_eq!(survey.samples_per_trace, 256);
        assert_eq!(survey.bits_per_sample, 8);
        assert_eq!(survey.header_offset, 1024);
    }

    #[test]
    fn test_parse_file_32bit() {
        let dzt = make_synthetic_dzt_file(128, 32, 1, 25);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_32bit.dzt");
        std::fs::write(&path, &dzt).unwrap();

        let survey = parse_file(path.to_str().unwrap()).unwrap();
        assert_eq!(survey.num_traces, 25);
        assert_eq!(survey.samples_per_trace, 128);
        assert_eq!(survey.bits_per_sample, 32);
    }

    #[test]
    fn test_parse_file_multi_channel() {
        let dzt = make_synthetic_dzt_file(256, 16, 2, 30);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_multi.dzt");
        std::fs::write(&path, &dzt).unwrap();

        let survey = parse_file(path.to_str().unwrap()).unwrap();
        assert_eq!(survey.num_traces, 30);
        assert_eq!(survey.samples_per_trace, 256);
        assert_eq!(survey.channels, 2);
    }

    #[test]
    fn test_parse_file_empty_trace_data() {
        // Header only, no trace data
        let buf = make_synthetic_dzt_header();
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("empty.dzt");
        std::fs::write(&path, &buf).unwrap();

        let survey = parse_file(path.to_str().unwrap()).unwrap();
        assert_eq!(survey.num_traces, 0);
    }

    #[test]
    fn test_parse_file_missing_file() {
        let result = parse_file("/nonexistent/file.dzt");
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_dzg_gpgga() {
        let nmea = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47";
        let result = parse_nmea_gpgga(nmea);
        assert!(result.is_some());
        let (lat, lon, alt) = result.unwrap();
        // 4807.038,N = 48 + 7.038/60 = 48.1173
        assert!((lat - 48.1173).abs() < 0.001);
        // 01131.000,E = 11 + 31.000/60 = 11.51667
        assert!((lon - 11.51667).abs() < 0.001);
        assert!((alt - 545.4).abs() < 0.01);
    }

    #[test]
    fn test_parse_dzg_gprmc() {
        let nmea = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A";
        let result = parse_nmea_gprmc(nmea);
        assert!(result.is_some());
        let (lat, lon, _alt) = result.unwrap();
        assert!((lat - 48.1173).abs() < 0.001);
        assert!((lon - 11.51667).abs() < 0.001);
    }

    #[test]
    fn test_parse_dzg_southern_hemisphere() {
        let nmea = "$GPGGA,123519,3356.000,S,01825.000,E,1,08,0.9,100.0,M,,*XX";
        let result = parse_nmea_gpgga(nmea);
        assert!(result.is_some());
        let (lat, lon, _alt) = result.unwrap();
        // 33°56.000'S = -(33 + 56/60) = -33.9333
        assert!((lat - (-33.9333)).abs() < 0.001);
        // 18°25.000'E = 18 + 25/60 = 18.41667
        assert!((lon - 18.41667).abs() < 0.001);
    }

    #[test]
    fn test_parse_dzg_western_hemisphere() {
        let nmea = "$GPRMC,123519,A,4916.450,N,12311.120,W,022.4,084.4,230394,003.1,W*6A";
        let result = parse_nmea_gprmc(nmea);
        assert!(result.is_some());
        let (lat, lon, _alt) = result.unwrap();
        // 49°16.450'N = 49 + 16.45/60 = 49.27417
        assert!((lat - 49.27417).abs() < 0.001);
        // 123°11.120'W = -(123 + 11.12/60) = -123.18533
        assert!((lon - (-123.18533)).abs() < 0.001);
    }

    #[test]
    fn test_parse_dzg_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dzg");
        let content = "\
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
$GPGGA,123520,4807.040,N,01131.010,E,1,08,0.9,546.0,M,46.9,M,,*48
$GPGGA,123521,4807.042,N,01131.020,E,1,08,0.9,546.5,M,46.9,M,,*49
";
        std::fs::write(&path, content).unwrap();

        let positions = parse_dzg(path.to_str().unwrap()).unwrap();
        assert_eq!(positions.len(), 3);
        assert_eq!(positions[0].0, 0);
        assert_eq!(positions[1].0, 1);
        assert_eq!(positions[2].0, 2);
        // Check lat/lon values
        assert!((positions[0].1 - 48.1173).abs() < 0.001);
        assert!((positions[0].2 - 11.51667).abs() < 0.001);
    }

    #[test]
    fn test_parse_dzg_empty_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("empty.dzg");
        std::fs::write(&path, "").unwrap();

        let positions = parse_dzg(path.to_str().unwrap()).unwrap();
        assert!(positions.is_empty());
    }

    #[test]
    fn test_parse_dzg_missing_file() {
        let result = parse_dzg("/nonexistent/file.dzg");
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_nmea_invalid_sentence() {
        assert!(parse_nmea_gpgga("not an NMEA sentence").is_none());
        assert!(parse_nmea_gprmc("not an NMEA sentence").is_none());
    }

    #[test]
    fn test_parse_nmea_empty_fields() {
        assert!(parse_nmea_gpgga("$GPGGA,,,,,,,,,,,").is_none());
        assert!(parse_nmea_gprmc("$GPRMC,,,,,,,,,,,").is_none());
    }
}