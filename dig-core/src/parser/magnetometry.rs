//! Bartington/Geoscan magnetometry format parser.
//!
//! Parses .dat (binary raster) and .grd (ASCII header) file pairs
//! from Bartington Grad601 and Geoscan FM256 instruments.
//!
//! The .grd file contains spatial metadata (origin, cell size, rotation).
//! The .dat file contains the raw magnetic gradient measurements as
//! int16 little-endian values in row-major order.
//!
//! Zig-zag traverses (alternating row direction) are automatically
//! detected and unspooled.

use crate::types::survey::PySurvey;

/// Void/sentinel value for missing data in magnetometry grids.
/// Bartington/Geoscan use -32768 (i16::MIN) or 32767 (i16::MAX).
pub const VOID_I16: i16 = i16::MIN;

/// Grid metadata parsed from .grd file.
#[derive(Debug, Clone)]
pub struct GridMetadata {
    pub rows: usize,
    pub cols: usize,
    pub cell_size: f32,
    pub origin_easting: f64,
    pub origin_northing: f64,
    pub rotation_deg: f32,
    pub zigzag: bool,
}

/// Parse a .grd ASCII header file.
pub fn parse_grd(path: &str) -> Result<GridMetadata, Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(path)?;
    let mut meta = GridMetadata {
        rows: 0,
        cols: 0,
        cell_size: 0.5,
        origin_easting: 0.0,
        origin_northing: 0.0,
        rotation_deg: 0.0,
        zigzag: true,
    };

    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') || line.starts_with("//") {
            continue;
        }
        let parts: Vec<&str> = line
            .splitn(2, |c: char| c == ' ' || c == '=' || c == ':')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .collect();
        if parts.len() < 2 {
            continue;
        }
        match parts[0].to_uppercase().as_str() {
            "ROWS" | "GRID_ROWS" | "NR" => {
                meta.rows = parts[1].parse()?;
            }
            "COLS" | "GRID_COLS" | "NC" => {
                meta.cols = parts[1].parse()?;
            }
            "CELL_SIZE" | "DX" | "DY" => {
                meta.cell_size = parts[1].parse()?;
            }
            "ORIGIN_EASTING" | "XE" => {
                meta.origin_easting = parts[1].parse()?;
            }
            "ORIGIN_NORTHING" | "YN" => {
                meta.origin_northing = parts[1].parse()?;
            }
            "ROTATION" | "ANGLE" => {
                meta.rotation_deg = parts[1].parse()?;
            }
            "ZIGZAG" => {
                meta.zigzag = parts[1].to_lowercase() == "true" || parts[1] == "1";
            }
            _ => {}
        }
    }

    if meta.rows == 0 || meta.cols == 0 {
        return Err("Invalid .grd file: missing rows/cols".into());
    }

    Ok(meta)
}

/// Parse a .dat binary file into a flat Vec<u8> of int16 values.
///
/// The .dat file is a flat binary array of magnetic gradient values.
/// Default assumption: int16 little-endian, row-major order.
/// Zig-zag traverses are unspooled by reversing every other row.
/// Void values (i16::MIN) are preserved for Python-side NaN handling.
pub fn parse_dat(
    path: &str,
    meta: &GridMetadata,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let raw = std::fs::read(path)?;
    let expected_bytes = meta.rows * meta.cols * 2; // int16
    if raw.len() < expected_bytes {
        return Err(format!(
            "File too small: {} bytes, expected at least {}",
            raw.len(),
            expected_bytes
        )
        .into());
    }

    // Read as int16 little-endian
    let mut values: Vec<i16> = Vec::with_capacity(meta.rows * meta.cols);
    for chunk in raw[..expected_bytes].chunks_exact(2) {
        let val = i16::from_le_bytes([chunk[0], chunk[1]]);
        values.push(val);
    }

    // Unspool zig-zag: reverse every other row
    if meta.zigzag {
        for row in 0..meta.rows {
            if row % 2 == 1 {
                let start = row * meta.cols;
                values[start..start + meta.cols].reverse();
            }
        }
    }

    // Return as raw bytes for Python-side numpy conversion
    let mut out = Vec::with_capacity(values.len() * 2);
    for v in &values {
        out.extend_from_slice(&v.to_le_bytes());
    }
    Ok(out)
}

/// Parse a .dat/.grd pair and return a PySurvey with grid data.
pub fn parse_file(
    dat_path: &str,
    grd_path: &str,
) -> Result<PySurvey, Box<dyn std::error::Error>> {
    let meta = parse_grd(grd_path)?;
    let data = parse_dat(dat_path, &meta)?;

    let mut survey = PySurvey::new(dat_path.to_string(), "magnetometry".to_string());
    survey.num_traces = meta.rows;
    survey.samples_per_trace = meta.cols;
    survey.bits_per_sample = 16;
    survey.channels = 1;
    survey.trace_data = data;
    // Store grid metadata in trace_positions as [rows, cols, cell_size, rotation_deg]
    survey.trace_positions = vec![
        meta.rows as f32,
        meta.cols as f32,
        meta.cell_size,
        meta.rotation_deg,
    ];
    // Store origin in trace_elevations as [easting, northing]
    survey.trace_elevations = vec![meta.origin_easting as f32, meta.origin_northing as f32];

    Ok(survey)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── .grd parser tests ─────────────────────────────────────────────

    #[test]
    fn test_parse_grd_full() {
        let content = "\
ROWS 100
COLS 50
CELL_SIZE 0.5
ORIGIN_EASTING 500000.0
ORIGIN_NORTHING 123450.0
ROTATION 15.0
ZIGZAG true
";
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.grd");
        std::fs::write(&path, content).unwrap();

        let meta = parse_grd(path.to_str().unwrap()).unwrap();
        assert_eq!(meta.rows, 100);
        assert_eq!(meta.cols, 50);
        assert!((meta.cell_size - 0.5).abs() < 0.01);
        assert!((meta.origin_easting - 500000.0).abs() < 0.01);
        assert!((meta.origin_northing - 123450.0).abs() < 0.01);
        assert!((meta.rotation_deg - 15.0).abs() < 0.01);
        assert!(meta.zigzag);
    }

    #[test]
    fn test_parse_grd_alternative_keys() {
        let content = "GRID_ROWS 64\nGRID_COLS 32\nDX 1.0\nDY 1.0\nXE 400000.0\nYN 200000.0\nANGLE 90.0\nZIGZAG false\n";
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.grd");
        std::fs::write(&path, content).unwrap();

        let meta = parse_grd(path.to_str().unwrap()).unwrap();
        assert_eq!(meta.rows, 64);
        assert_eq!(meta.cols, 32);
        assert!((meta.cell_size - 1.0).abs() < 0.01);
        assert!(!meta.zigzag);
    }

    #[test]
    fn test_parse_grd_missing_rows() {
        let content = "COLS 10\n";
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("bad.grd");
        std::fs::write(&path, content).unwrap();

        let result = parse_grd(path.to_str().unwrap());
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_grd_with_comments() {
        let content = "# Survey metadata\nROWS 20\n// Another comment\nCOLS 15\n";
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.grd");
        std::fs::write(&path, content).unwrap();

        let meta = parse_grd(path.to_str().unwrap()).unwrap();
        assert_eq!(meta.rows, 20);
        assert_eq!(meta.cols, 15);
    }

    // ── .dat parser tests ─────────────────────────────────────────────

    fn make_synthetic_dat(rows: usize, cols: usize, zigzag: bool) -> (Vec<u8>, GridMetadata) {
        let mut data = Vec::new();
        for i in 0..(rows * cols) as i16 {
            data.extend_from_slice(&i.to_le_bytes());
        }
        let meta = GridMetadata {
            rows,
            cols,
            cell_size: 0.5,
            origin_easting: 0.0,
            origin_northing: 0.0,
            rotation_deg: 0.0,
            zigzag,
        };
        (data, meta)
    }

    #[test]
    fn test_parse_dat_no_zigzag() {
        let (data, meta) = make_synthetic_dat(3, 4, false);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dat");
        std::fs::write(&path, &data).unwrap();

        let result = parse_dat(path.to_str().unwrap(), &meta).unwrap();
        // 3 rows × 4 cols × 2 bytes = 24 bytes
        assert_eq!(result.len(), 24);

        // Verify values are in original order
        let values: Vec<i16> = result
            .chunks_exact(2)
            .map(|c| i16::from_le_bytes([c[0], c[1]]))
            .collect();
        assert_eq!(values[0], 0);
        assert_eq!(values[5], 5);
        assert_eq!(values[11], 11);
    }

    #[test]
    fn test_parse_dat_zigzag() {
        let (data, meta) = make_synthetic_dat(4, 3, true);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.dat");
        std::fs::write(&path, &data).unwrap();

        let result = parse_dat(path.to_str().unwrap(), &meta).unwrap();
        let values: Vec<i16> = result
            .chunks_exact(2)
            .map(|c| i16::from_le_bytes([c[0], c[1]]))
            .collect();

        // Row 0 (even): 0, 1, 2 (unchanged)
        assert_eq!(values[0], 0);
        assert_eq!(values[1], 1);
        assert_eq!(values[2], 2);

        // Row 1 (odd): reversed — 5, 4, 3
        assert_eq!(values[3], 5);
        assert_eq!(values[4], 4);
        assert_eq!(values[5], 3);

        // Row 2 (even): 6, 7, 8 (unchanged)
        assert_eq!(values[6], 6);
        assert_eq!(values[7], 7);
        assert_eq!(values[8], 8);

        // Row 3 (odd): reversed — 11, 10, 9
        assert_eq!(values[9], 11);
        assert_eq!(values[10], 10);
        assert_eq!(values[11], 9);
    }

    #[test]
    fn test_parse_dat_too_small() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("tiny.dat");
        std::fs::write(&path, &[0u8; 2]).unwrap();

        let meta = GridMetadata {
            rows: 10,
            cols: 10,
            cell_size: 0.5,
            origin_easting: 0.0,
            origin_northing: 0.0,
            rotation_deg: 0.0,
            zigzag: false,
        };

        let result = parse_dat(path.to_str().unwrap(), &meta);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_dat_void_values() {
        let mut data = Vec::new();
        // 2×2 grid with one void value
        data.extend_from_slice(&0i16.to_le_bytes());
        data.extend_from_slice(&VOID_I16.to_le_bytes());
        data.extend_from_slice(&2i16.to_le_bytes());
        data.extend_from_slice(&3i16.to_le_bytes());

        let meta = GridMetadata {
            rows: 2,
            cols: 2,
            cell_size: 0.5,
            origin_easting: 0.0,
            origin_northing: 0.0,
            rotation_deg: 0.0,
            zigzag: false,
        };

        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("void.dat");
        std::fs::write(&path, &data).unwrap();

        let result = parse_dat(path.to_str().unwrap(), &meta).unwrap();
        let values: Vec<i16> = result
            .chunks_exact(2)
            .map(|c| i16::from_le_bytes([c[0], c[1]]))
            .collect();

        assert_eq!(values[0], 0);
        assert_eq!(values[1], VOID_I16);
        assert_eq!(values[2], 2);
        assert_eq!(values[3], 3);
    }

    // ── File pair tests ───────────────────────────────────────────────

    #[test]
    fn test_parse_file_basic() {
        let dir = tempfile::tempdir().unwrap();

        // Create .grd
        let grd_path = dir.path().join("test.grd");
        std::fs::write(&grd_path, "ROWS 4\nCOLS 3\nCELL_SIZE 0.5\nZIGZAG true\n").unwrap();

        // Create .dat (4×3 = 12 int16 values)
        let mut dat = Vec::new();
        for i in 0..12i16 {
            dat.extend_from_slice(&i.to_le_bytes());
        }
        let dat_path = dir.path().join("test.dat");
        std::fs::write(&dat_path, &dat).unwrap();

        let survey = parse_file(
            dat_path.to_str().unwrap(),
            grd_path.to_str().unwrap(),
        )
        .unwrap();

        assert_eq!(survey.num_traces, 4); // rows
        assert_eq!(survey.samples_per_trace, 3); // cols
        assert_eq!(survey.bits_per_sample, 16);
        assert_eq!(survey.format, "magnetometry");
        assert!(!survey.trace_data.is_empty());
        // 4 × 3 × 2 = 24 bytes
        assert_eq!(survey.trace_data.len(), 24);

        // Grid metadata stored in trace_positions
        assert!((survey.trace_positions[0] - 4.0).abs() < 0.01); // rows
        assert!((survey.trace_positions[1] - 3.0).abs() < 0.01); // cols
        assert!((survey.trace_positions[2] - 0.5).abs() < 0.01); // cell_size
    }

    #[test]
    fn test_parse_file_missing_grd() {
        let result = parse_file("/nonexistent.dat", "/nonexistent.grd");
        assert!(result.is_err());
    }
}