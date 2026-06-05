"""Tests for DIG signal processing pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
from dig.processing.time_zero import (
    find_time_zero_mer,
    find_time_zero_threshold,
    correct_time_zero,
)
from dig.processing.dewow import dewow_fft, dewow_median
from dig.processing.background import remove_background_global, remove_background_local
from dig.processing.bandpass import bandpass_butterworth
from dig.processing.gain import sec_gain, agc, linear_gain
from dig.processing.topography import correct_topography_shift
from dig.processing.magnetometry import destagger, despike, destripe


class TestTimeZero:
    def test_mer_finds_peak(self):
        trace = np.zeros(100)
        trace[20:40] = np.sin(np.linspace(0, np.pi, 20)) ** 2
        t0 = find_time_zero_mer(trace)
        assert 20 <= t0 <= 30  # MER finds the inflection point near the onset

    def test_threshold_finds_crossing(self):
        trace = np.zeros(100)
        trace[30] = 10.0
        # Add small noise so noise floor is non-zero
        rng = np.random.default_rng(42)
        trace[:10] = rng.normal(0, 0.01, 10)
        t0 = find_time_zero_threshold(trace, threshold=3.0)
        assert t0 == 30

    def test_correct_time_zero_constant(self):
        data = np.zeros((5, 100))
        data[:, 50] = 1.0
        corrected = correct_time_zero(data, 10)
        assert corrected.shape == data.shape
        assert corrected[0, 40] == 1.0  # shifted by 10


class TestDewow:
    def test_dewow_fft_removes_dc(self):
        data = np.ones((3, 100)) * 5.0
        result = dewow_fft(data, sample_rate=1000.0, cutoff_hz=0.5)
        assert np.all(np.abs(result) < 0.1)

    def test_dewow_median_removes_dc(self):
        data = np.ones((3, 100)) * 5.0
        result = dewow_median(data, window_size=11)
        assert np.all(np.abs(result) < 0.1)


class TestBackground:
    def test_global_removes_horizontal_bands(self):
        data = np.ones((10, 50)) * 3.0
        # Add a localized anomaly (only in 1 trace out of 10)
        data[0, 10] = 10.0
        result = remove_background_global(data)
        # Background (constant 3.0) should be removed from unaffected traces
        assert np.all(np.abs(result[1:, :10]) < 0.1)
        # Localized anomaly should be preserved (10 - 3.7 = 6.3)
        assert np.abs(result[0, 10] - 6.3) < 0.2

    def test_local_adapts(self):
        data = np.random.randn(20, 50)
        result = remove_background_local(data, window_traces=5)
        assert result.shape == data.shape


class TestBandpass:
    def test_bandpass_preserves_sine(self):
        t = np.linspace(0, 1, 500)
        data = np.sin(2 * np.pi * 10 * t)  # 10 Hz sine
        data_2d = data[np.newaxis, :]
        result = bandpass_butterworth(data_2d, sample_rate=500, low_cut=5, high_cut=20)
        assert np.abs(np.corrcoef(data, result[0])[0, 1]) > 0.9


class TestGain:
    def test_sec_gain_increases_with_depth(self):
        data = np.ones((1, 100))
        result = sec_gain(data, sample_rate=1000.0, alpha=0.5)
        assert result[0, -1] > result[0, 0]

    def test_agc_normalizes(self):
        data = np.ones((1, 100)) * 5.0
        result = agc(data, window_samples=20)
        assert np.all(np.abs(result - 1.0) < 0.1)

    def test_linear_gain_increases(self):
        data = np.ones((1, 100))
        result = linear_gain(data, gain_db_per_us=10.0, sample_rate=1e9)
        assert result[0, -1] > result[0, 0]


class TestTopography:
    def test_correct_topography_shift(self):
        data = np.ones((10, 100))
        elevations = np.linspace(0, 5, 10)
        result = correct_topography_shift(data, elevations, velocity_m_ns=0.1, sample_interval_ns=0.1)
        assert result.shape == data.shape


class TestMagnetometry:
    def test_destagger(self):
        data = np.zeros((4, 10))
        data[1, 0] = 1.0
        result = destagger(data, shift=1)
        assert result[1, 1] == 1.0  # shifted by 1

    def test_despike(self):
        data = np.zeros((10, 10))
        data[5, 5] = 100.0
        result = despike(data, threshold=3.0)
        assert result[5, 5] < 10.0  # spike removed

    def test_destripe_median(self):
        data = np.ones((10, 10)) * 5.0
        data[3, :] = 10.0  # stripe
        result = destripe(data, method="median")
        assert np.abs(result[3, 0]) < 0.1  # stripe removed