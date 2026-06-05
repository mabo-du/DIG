//! Survey data structures exposed to Python via PyO3.

use pyo3::prelude::*;

/// A single processing step in the audit trail.
#[pyclass(get_all, set_all)]
#[derive(Clone, Debug)]
pub struct PyProcessingStep {
    pub name: String,
    pub parameters: String, // JSON-serialized parameters
    pub timestamp: f64,     // Unix timestamp
    pub software_version: String,
}

/// A geophysical survey — the core data model.
///
/// Holds memory-mapped trace data, header metadata, coordinate system,
/// and an immutable processing history DAG.
#[pyclass(get_all)]
#[derive(Clone, Debug)]
pub struct PySurvey {
    pub path: String,
    pub format: String,          // "dzt", "dt1", "dat", "sgy"
    pub num_traces: usize,
    pub samples_per_trace: usize,
    pub bits_per_sample: u8,
    pub sample_interval_ns: f32,
    pub traces_per_second: f32,
    pub traces_per_meter: f32,
    pub time_zero_ns: f32,
    pub time_window_ns: f32,
    pub channels: u16,
    pub header_offset: usize,
    pub history: Vec<PyProcessingStep>,
}

#[pymethods]
impl PySurvey {
    #[new]
    pub fn new(path: String, format: String) -> Self {
        PySurvey {
            path,
            format,
            num_traces: 0,
            samples_per_trace: 0,
            bits_per_sample: 16,
            sample_interval_ns: 0.0,
            traces_per_second: 0.0,
            traces_per_meter: 0.0,
            time_zero_ns: 0.0,
            time_window_ns: 0.0,
            channels: 1,
            header_offset: 0,
            history: Vec::new(),
        }
    }

    /// Append a processing step to the audit trail.
    fn add_step(&mut self, name: &str, parameters: &str) {
        let step = PyProcessingStep {
            name: name.to_string(),
            parameters: parameters.to_string(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64(),
            software_version: env!("CARGO_PKG_VERSION").to_string(),
        };
        self.history.push(step);
    }

    /// Return the processing history as a list of dicts.
    fn get_history(&self) -> Vec<PyProcessingStep> {
        self.history.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "PySurvey(format={}, traces={}, samples={}, bits={})",
            self.format, self.num_traces, self.samples_per_trace, self.bits_per_sample
        )
    }
}