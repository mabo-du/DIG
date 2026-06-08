//! dig-core — High-performance Rust backend for DIG geophysics processing.
//!
//! Provides memory-safe binary format parsers, SIMD-accelerated signal
//! processing, and memory-mapped I/O — exposed to Python via PyO3.

mod parser;
pub mod dsp;
mod io;
mod types;

use pyo3::prelude::*;

/// DIG core Python module.
#[pymodule]
fn dig_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<types::survey::PySurvey>()?;
    m.add_class::<types::survey::PyProcessingStep>()?;
    m.add_function(wrap_pyfunction!(parse_dzt, m)?)?;
    m.add_function(wrap_pyfunction!(parse_dt1, m)?)?;
    m.add_function(wrap_pyfunction!(parse_dzg, m)?)?;
    m.add_function(wrap_pyfunction!(parse_magnetometry, m)?)?;
    m.add_function(wrap_pyfunction!(apply_dewow, m)?)?;
    m.add_function(wrap_pyfunction!(apply_bandpass, m)?)?;
    m.add_function(wrap_pyfunction!(apply_sec_gain, m)?)?;
    m.add_function(wrap_pyfunction!(apply_agc, m)?)?;
    m.add_function(wrap_pyfunction!(apply_kirchhoff_migration, m)?)?;
    Ok(())
}

// ── Parser entry points ──────────────────────────────────────────────

#[pyfunction]
fn parse_dzt(path: &str) -> PyResult<PyObject> {
    let survey = parser::dzt::parse_file(path)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    Ok(Python::with_gil(|py| survey.into_py(py)))
}

#[pyfunction]
#[pyo3(signature = (path, hd_content=None))]
fn parse_dt1(path: &str, hd_content: Option<&str>) -> PyResult<PyObject> {
    let survey = parser::dt1::parse_file(path, hd_content)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    Ok(Python::with_gil(|py| survey.into_py(py)))
}

#[pyfunction]
fn parse_dzg(path: &str) -> PyResult<Vec<(usize, f64, f64, f64)>> {
    parser::dzt::parse_dzg(path)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
}

#[pyfunction]
fn parse_magnetometry(dat_path: &str, grd_path: &str) -> PyResult<PyObject> {
    let survey = parser::magnetometry::parse_file(dat_path, grd_path)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    Ok(Python::with_gil(|py| survey.into_py(py)))
}

// ── DSP entry points ─────────────────────────────────────────────────

#[pyfunction]
fn apply_dewow(data: Vec<f32>, window_size: usize) -> Vec<f32> {
    dsp::filter::dewow(&data, window_size)
}

#[pyfunction]
fn apply_bandpass(data: Vec<f32>, sample_rate: f32, low_cut: f32, high_cut: f32) -> Vec<f32> {
    dsp::filter::bandpass(&data, sample_rate, low_cut, high_cut)
}

#[pyfunction]
fn apply_sec_gain(data: Vec<f32>, sample_rate: f32, alpha: f32) -> Vec<f32> {
    dsp::filter::sec_gain(&data, sample_rate, alpha)
}

#[pyfunction]
fn apply_agc(data: Vec<f32>, window_size: usize) -> Vec<f32> {
    dsp::filter::agc(&data, window_size)
}

#[pyfunction]
#[pyo3(signature = (data, velocity_m_ns=0.1, sample_interval_ns=0.1, trace_spacing_m=0.05, aperture_traces=30))]
fn apply_kirchhoff_migration<'py>(
    py: Python<'py>,
    data: numpy::PyReadonlyArray2<'py, f64>,
    velocity_m_ns: f64,
    sample_interval_ns: f64,
    trace_spacing_m: f64,
    aperture_traces: usize,
) -> pyo3::Bound<'py, numpy::PyArray2<f64>> {
    let array_view = data.as_array();
    let result = dsp::migration::kirchhoff_migration(
        array_view,
        velocity_m_ns,
        sample_interval_ns,
        trace_spacing_m,
        aperture_traces,
    );
    use numpy::IntoPyArray;
    result.into_pyarray_bound(py)
}