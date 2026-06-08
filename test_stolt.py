import numpy as np
from scipy import fft, signal
import matplotlib.pyplot as plt

def stolt_migration_fixed(
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

    # To avoid dimensionality issues, let's use cyclic everywhere.
    # f is in Hz. kx is in cycles/m.
    # The relation is: f_in^2 = f_out^2 + (v * kx / 2)^2
    # So we need to map from f_in to f_out for each kx.
    # Wait, spec is defined at (kx, f_in). We want migrated_spec at (kx, f_out).
    # Since we use IFFT2 to get back to (x, t), our output "frequency" axis 
    # is actually f_out (which corresponds to unmigrated time t0).
    # For a given target frequency f_out and wavenumber kx:
    # f_in = sign(f_out) * sqrt(f_out^2 + (v * kx / 2)^2)
    
    # Let's create grids
    F_out, Kx = np.meshgrid(f, kx, indexing='ij') # Wait, shape of spec is (n_t_pad, n_s_pad)
    # so spec[ix, i_f]
    Kx, F_out = np.meshgrid(kx, f, indexing='ij')
    
    # calculate required input frequency
    F_in = np.sign(F_out) * np.sqrt(F_out**2 + (v * Kx / 2)**2)
    
    # Now we need to interpolate `spec` along the frequency axis.
    # `f` is the array of input frequencies.
    # Note that `f` from fftfreq is not strictly increasing. It goes 0, df, ..., fNyq, -fNyq, ..., -df
    # We should use fftshift, interpolate, and ifftshift.
    
    spec_shifted = fft.fftshift(spec, axes=1)
    f_shifted = fft.fftshift(f)
    
    migrated_spec = np.zeros_like(spec_shifted)
    
    # 1D interpolation along the frequency axis for each kx
    for i in range(n_t_pad):
        # We want to evaluate spec_shifted[i, :] at frequencies F_in[i, :]
        # using f_shifted as the coordinates
        f_in_i = F_in[i, :]
        
        # Scaling factor for amplitude preservation (optional but standard)
        # Obliquity factor: d(f_in)/d(f_out) = f_out / f_in
        # avoiding division by zero
        # scale = np.abs(F_out[i, :]) / np.maximum(np.abs(f_in_i), 1e-10)
        
        migrated_spec[i, :] = np.interp(f_in_i, f_shifted, spec_shifted[i, :]) 
        # Wait, np.interp only handles real values. We need complex interpolation.
    
    # complex interp
    for i in range(n_t_pad):
        f_in_i = F_in[i, :]
        real_part = np.interp(f_in_i, f_shifted, np.real(spec_shifted[i, :]))
        imag_part = np.interp(f_in_i, f_shifted, np.imag(spec_shifted[i, :]))
        scale = np.abs(F_out[i, :]) / np.maximum(np.abs(f_in_i), 1e-10)
        migrated_spec[i, :] = (real_part + 1j * imag_part) * scale

    migrated_spec_unshifted = fft.ifftshift(migrated_spec, axes=1)
    migrated = fft.ifft2(migrated_spec_unshifted)

    return np.real(migrated[:n_traces, :n_samples])

