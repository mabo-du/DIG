import numpy as np
from scipy import fft
from scipy.interpolate import interp1d

def stolt_migration_vec(
    data: np.ndarray,
    velocity_m_ns: float = 0.1,
    sample_interval_ns: float = 0.1,
    trace_spacing_m: float = 0.05,
) -> np.ndarray:
    data = np.asarray(data, dtype=np.float64)
    n_traces, n_samples = data.shape

    n_t_pad = 2 ** int(np.ceil(np.log2(n_traces)))
    n_s_pad = 2 ** int(np.ceil(np.log2(n_samples)))
    padded = np.zeros((n_t_pad, n_s_pad))
    padded[:n_traces, :n_samples] = data

    spec = fft.fft2(padded)

    dt = sample_interval_ns * 1e-9
    dx = trace_spacing_m
    f = fft.fftfreq(n_s_pad, d=dt)
    kx = fft.fftfreq(n_t_pad, d=dx)

    v = velocity_m_ns * 1e9

    Kx, F_out = np.meshgrid(kx, f, indexing='ij')
    F_in = np.sign(F_out) * np.sqrt(F_out**2 + (v * Kx / 2)**2)

    spec_shifted = fft.fftshift(spec, axes=1)
    f_shifted = fft.fftshift(f)

    # We can use interp1d, but F_in varies per trace (row).
    # Since F_in is different for each row, we either loop or use map_coordinates.
    migrated_spec = np.zeros_like(spec_shifted)
    
    for i in range(n_t_pad):
        f_in_i = F_in[i, :]
        real_part = np.interp(f_in_i, f_shifted, np.real(spec_shifted[i, :]))
        imag_part = np.interp(f_in_i, f_shifted, np.imag(spec_shifted[i, :]))
        scale = np.abs(F_out[i, :]) / np.maximum(np.abs(f_in_i), 1e-10)
        migrated_spec[i, :] = (real_part + 1j * imag_part) * scale

    migrated_spec_unshifted = fft.ifftshift(migrated_spec, axes=1)
    migrated = fft.ifft2(migrated_spec_unshifted)

    return np.real(migrated[:n_traces, :n_samples])

