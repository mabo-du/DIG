use ndarray::{Array2, ArrayView2};

pub fn kirchhoff_migration(
    data: ArrayView2<f64>,
    velocity_m_ns: f64,
    sample_interval_ns: f64,
    trace_spacing_m: f64,
    aperture_traces: usize,
) -> Array2<f64> {
    let (n_traces, n_samples) = (data.nrows(), data.ncols());
    let mut result = Array2::<f64>::zeros((n_traces, n_samples));

    let v = velocity_m_ns * 1e9;
    let dt = sample_interval_ns * 1e-9;

    for i in 0..n_traces {
        for j in 0..n_samples {
            let t0 = (j as f64) * dt;
            if t0 <= 0.0 {
                continue;
            }

            let mut amplitude = 0.0;
            let mut count = 0;

            let k_start = i.saturating_sub(aperture_traces);
            let k_end = std::cmp::min(n_traces, i + aperture_traces + 1);

            for k in k_start..k_end {
                let dx = (k.abs_diff(i) as f64) * trace_spacing_m;
                let t = (t0 * t0 + (2.0 * dx / v).powi(2)).sqrt();
                let t_sample = t / dt;
                
                if t_sample >= 0.0 && t_sample < (n_samples - 1) as f64 {
                    let idx = t_sample.trunc() as usize;
                    let frac = t_sample - t_sample.trunc();
                    
                    let amp = data[[k, idx]] * (1.0 - frac) + data[[k, idx + 1]] * frac;
                    amplitude += amp;
                    count += 1;
                }
            }

            result[[i, j]] = amplitude / (if count > 0 { count as f64 } else { 1.0 });
        }
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::Array2;

    #[test]
    fn test_kirchhoff_migration() {
        let mut data = Array2::<f64>::zeros((10, 10));
        data[[5, 5]] = 1.0;
        let migrated = kirchhoff_migration(data.view(), 0.1, 0.1, 0.05, 5);
        assert_eq!(migrated.shape(), &[10, 10]);
    }
}
