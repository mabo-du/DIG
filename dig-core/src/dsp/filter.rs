//! Signal processing filter implementations.
//!
//! All filters operate on flat f32 slices. Edge effects are handled
//! via padding rather than truncation.

use rustfft::{FftPlanner, num_complex::Complex};

/// Apply a de-wow (high-pass) filter using a running mean.
///
/// Subtracts the local mean within a sliding window of `window_size`
/// samples from each sample. This removes low-frequency inductive
/// coupling drift ("wow") while preserving high-frequency reflections.
///
/// Edge handling: window is truncated at boundaries (no padding).
pub fn dewow(data: &[f32], window_size: usize) -> Vec<f32> {
    let half = window_size / 2;
    let len = data.len();
    let mut result = vec![0.0f32; len];

    for i in 0..len {
        let start = i.saturating_sub(half);
        let end = (i + half).min(len);
        let window = &data[start..end];
        let mean: f32 = window.iter().sum::<f32>() / window.len() as f32;
        result[i] = data[i] - mean;
    }

    result
}

/// Apply a bandpass filter using a raised-cosine (Tukey) window in the
/// frequency domain.
///
/// Unlike a rectangular window (which introduces Gibbs ringing), the
/// raised-cosine transition provides smooth roll-off at the passband
/// edges, eliminating ringing artifacts.
///
/// This is a zero-phase filter (forward FFT → mask → inverse FFT).
pub fn bandpass(data: &[f32], sample_rate: f32, low_cut: f32, high_cut: f32) -> Vec<f32> {
    let len = data.len();
    let mut planner = FftPlanner::new();
    let fft = planner.plan_fft_forward(len);
    let ifft = planner.plan_fft_inverse(len);

    // Convert to complex
    let mut spectrum: Vec<Complex<f32>> = data.iter().map(|&x| Complex::new(x, 0.0)).collect();

    // Forward FFT
    fft.process(&mut spectrum);

    // Apply raised-cosine (Tukey) bandpass mask
    let transition_width = 0.1; // 10% of passband for roll-off
    for (i, bin) in spectrum.iter_mut().enumerate() {
        let freq = (i as f32 / len as f32) * sample_rate;

        if freq >= low_cut && freq <= high_cut {
            // Passband — full amplitude
            // (keep as-is)
        } else if freq < low_cut {
            // Low-frequency stopband — smooth roll-off
            let dist = (low_cut - freq) / (low_cut * transition_width).max(1.0);
            let gain = if dist < 1.0 {
                0.5 * (1.0 + (dist * std::f32::consts::PI).cos())
            } else {
                0.0
            };
            *bin = Complex::new(bin.re * gain, bin.im * gain);
        } else {
            // High-frequency stopband — smooth roll-off
            let dist = (freq - high_cut) / (high_cut * transition_width).max(1.0);
            let gain = if dist < 1.0 {
                0.5 * (1.0 + (dist * std::f32::consts::PI).cos())
            } else {
                0.0
            };
            *bin = Complex::new(bin.re * gain, bin.im * gain);
        }
    }

    // Inverse FFT
    ifft.process(&mut spectrum);

    // Normalize and return real part
    spectrum.iter().map(|c| c.re / len as f32).collect()
}

/// Apply Spreading and Exponential Compensation (SEC) gain.
///
/// Models the physical attenuation equation: A(t) = A₀ · t · exp(α·t)
/// where t is time and α is the attenuation coefficient.
///
/// This preserves relative amplitude ratios (unlike AGC).
pub fn sec_gain(data: &[f32], sample_rate: f32, alpha: f32) -> Vec<f32> {
    let dt = 1.0 / sample_rate;
    data.iter()
        .enumerate()
        .map(|(i, &sample)| {
            let t = i as f32 * dt;
            let gain = t * (alpha * t).exp();
            sample * gain
        })
        .collect()
}

/// Apply Automatic Gain Control (AGC).
///
/// Normalizes each sample by the RMS amplitude within a sliding window.
/// Note: This destroys relative amplitude information — use SEC for
/// stratigraphic analysis where amplitude ratios matter.
pub fn agc(data: &[f32], window_size: usize) -> Vec<f32> {
    let half = window_size / 2;
    let len = data.len();
    let mut result = vec![0.0f32; len];

    for i in 0..len {
        let start = i.saturating_sub(half);
        let end = (i + half).min(len);
        let window = &data[start..end];
        let rms = (window.iter().map(|&x| x * x).sum::<f32>() / window.len() as f32)
            .sqrt()
            .max(1e-10);
        result[i] = data[i] / rms;
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dewow_constant_signal() {
        let data = vec![1.0f32; 100];
        let result = dewow(&data, 10);
        // Constant signal should be completely removed
        for v in &result {
            assert!((*v).abs() < 1e-6);
        }
    }

    #[test]
    fn test_dewow_preserves_impulse() {
        let mut data = vec![0.0f32; 100];
        data[50] = 10.0;
        let result = dewow(&data, 10);
        // Impulse should be preserved (approximately)
        assert!(result[50].abs() > 5.0);
    }

    #[test]
    fn test_sec_gain_positive() {
        let data = vec![1.0f32; 50];
        let result = sec_gain(&data, 100.0, 0.5);
        // Gain should increase with time (deeper = more amplification)
        assert!(result[1] > 0.0);
        assert!(result[49] > result[1]);
    }

    #[test]
    fn test_agc_constant_signal() {
        let data = vec![5.0f32; 100];
        let result = agc(&data, 20);
        // AGC on constant signal should produce ~1.0
        for v in &result {
            assert!((*v - 1.0).abs() < 0.1);
        }
    }
}