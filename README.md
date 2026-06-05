# DIG — Digital Imaging for Geophysics

An open-source suite for processing, analyzing, and visualizing Ground Penetrating Radar (GPR) and Magnetometry data for archaeological prospection.

## Quick Start

```bash
# Install
pip install dig

# Process a GSSI .DZT file
from dig.parsers import DZTFile
from dig.processing import dewow, background, gain

dzt = DZTFile("survey.dzt")
data = dzt.traces
data = dewow.dewow_fft(data, sample_rate=1e9)
data = background.remove_background_global(data)
data = gain.sec_gain(data, sample_rate=1e9)
```

## Architecture

```
dig/              # Python package (GUI, orchestration, export)
├── core/         # Rust bindings (PyO3)
├── parsers/      # Format parsers (DZT, DT1, magnetometry, SEG-Y)
├── processing/   # Signal processing pipeline (DAG-based, immutable)
├── viz/          # PySide6 + PyQtGraph + PyVista visualization
├── export/       # GeoTIFF, CSV, GeoJSON, QGIS project export
└── models/       # Data models (Survey, Profile, Grid3D, AuditTrail)

dig-core/         # Rust crate (performance-critical code)
├── parser/       # Binary format parsers (nom-based)
├── dsp/          # SIMD-accelerated signal processing
└── io/           # Memory-mapped file I/O
```

## Supported Formats

| Format | Instrument | Status |
|--------|-----------|--------|
| .DZT | GSSI SIR-3000/4000 | ✅ Phase 1 |
| .DT1/.HD | Sensors & Software Pulse EKKO | ✅ Phase 1 |
| .dat/.grd | Bartington Grad601 / Geoscan FM256 | ✅ Phase 1 |
| .sgy | SEG-Y (interoperability) | ✅ Phase 1 |

## Processing Pipeline

- Time-zero correction (MER, threshold, manual)
- De-wow (FFT high-pass, running median)
- Background removal (global, localized)
- Bandpass filtering (Butterworth, zero-phase)
- Gain (SEC, AGC, linear)
- Topographic correction
- Stolt/Kirchhoff migration
- Magnetometry: destagger, despike, destripe, interpolation

## Export

- GeoTIFF (multi-band, rotated, proper CRS)
- Cloud-Optimized GeoTIFF (COG)
- CSV, GeoJSON, GeoPackage
- QGIS project file (.qgs)

## License

MIT

## Ecosystem

DIG is part of a broader open-source digital heritage ecosystem. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for integration points with LiDAR-Relief, StratiGraph, Paleo, Fritts, HOARD, and the Tollense Rosetta Stone Initiative.