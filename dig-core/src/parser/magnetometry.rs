//! Bartington/Geoscan magnetometry format parser.
//!
//! Parses .dat (binary raster) and .grd (ASCII header) file pairs
//! from Bartington Grad601 and Geoscan FM256 instruments.
//!
//! The .grd file contains spatial metadata (origin, cell size, rotation).
//! The .dat file contains the raw magnetic gradient measurements.

use crate::types::survey::PySurvey;

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
        let parts: Vec<&str> = line.splitn(2, |c: char| c == ' ' || c == '=' || c == ':')
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

/// Parse a .dat binary file into a 2D grid.
///
/// The .dat file is a flat binary array of magnetic gradient values.
/// Default assumption: int16 little-endian, row-major order.
/// Zig-zag traverses are unspooled by reversing every other row.
pub fn parse_dat(
    path: &str,
    meta: &GridMetadata,
) -> Result<Vec<f32>, Box<dyn std::error::Error>> {
    let raw = std::fs::read(path)?;
    let expected_bytes = meta.rows * meta.cols * 2; // int16
    if raw.len() < expected_bytes {
        return Err(format!(
            "File too small: {} bytes, expected at least {}",
            raw.len(),
            expected_bytes
        ).into());
    }

    // Read as int16 little-endian
    let mut values: Vec<f32> = Vec::with_capacity(meta.rows * meta.cols);
    for chunk in raw[..expected_bytes].chunks_exact(2) {
        let val = i16::from_le_bytes([chunk[0], chunk[1]]);
        values.push(val as f32);
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

    Ok(values)
}

/// Parse a .dat/.grd pair and return a PySurvey.
pub fn parse_file(dat_path: &str, grd_path: &str) -> Result<PySurvey, Box<dyn std::error::Error>> {
    let meta = parse_grd(grd_path)?;
    let values = parse_dat(dat_path, &meta)?;

    let mut survey = PySurvey::new(dat_path.to_string(), "magnetometry".to_string());
    survey.num_traces = meta.rows * meta.cols;
    survey.samples_per_trace = 1;
    survey.bits_per_sample = 16;
    survey.channels = 1;

    Ok(survey)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write as _;

    #[test]
    fn test_parse_grd() {
        let grd_content = "\
ROWS 100
COLS 50
CELL_SIZE 0.5
ORIGIN_EASTING 500000.0
ORIGIN_NORTHING 123450.0
ROTATION 15.0
ZIGZAG true
";
        let dir = tempfile::tempdir().unwrap();
        let grd_path = dir.path().join("test.grd");
        std::fs::write(&grd_path, grd_content).unwrap();

        let meta = parse_grd(grd_path.to_str().unwrap()).unwrap();
        assert_eq!(meta.rows, 100);
        assert_eq!(meta.cols, 50);
        assert!((meta.cell_size - 0.5).abs() < 0.01);
        assert!(meta.zigzag);
    }

    #[test]
    fn test_parse_dat_zigzag() {
        let dir = tempfile::tempdir().unwrap();
        let dat_path = dir.path().join("test.dat");

        // Create a 4×3 grid with known values
        let mut data = Vec::new();
        for i in 0..12i16 {
            data.extend_from_slice(&i.to_le_bytes());
        }
        std::fs::write(&dat_path, &data).unwrap();

        let meta = GridMetadata {
            rows: 4,
            cols: 3,
            cell_size: 0.5,
            origin_easting: 0.0,
            origin_northing: 0.0,
            rotation_deg: 0.0,
            zigzag: true,
        };

        let values = parse_dat(dat_path.to_str().unwrap(), &meta).unwrap();
        assert_eq!(values.len(), 12);

        // Row 0 (even): should be 0, 1, 2 (unchanged)
        assert_eq!(values[0], 0.0);
        assert_eq!(values[1], 1.0);
        assert_eq!(values[2], 2.0);

        // Row 1 (odd): should be reversed — 5, 4, 3
        assert_eq!(values[3], 5.0);
        assert_eq!(values[4], 4.0);
        assert_eq!(values[5], 3.0);
    }
}