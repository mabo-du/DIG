# DIG — Digital Imaging for Geophysics

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/mark/DIG)](https://github.com/mark/DIG/releases)
[![PyPI version](https://badge.fury.io/py/dig.svg)](https://badge.fury.io/py/dig)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An open-source suite for processing, analyzing, and visualizing Ground Penetrating Radar (GPR) and Magnetometry data for archaeological prospection.

DIG bridges the gap between high-performance geophysical processing and user-friendly archaeological interpretation, utilizing a **Rust-based DSP backend** and a rich **PySide6 / PyVista 3D visualization frontend**.

## 📖 Documentation

The full documentation—including the User Guide, API Reference, and Integration Guides—is available at: **[DIG Documentation](https://mabo-du.github.io/DIG)**

## 🚀 Quick Start

### Installation

For most users, simply install DIG via PyPI:
```bash
pip install dig
```

*Alternatively, you can download pre-compiled standalone executables (Windows `.exe`, macOS `.dmg`, Linux `AppImage`) from our [Releases page](https://github.com/mark/DIG/releases).*

### Python API Example

```python
from dig.parsers import DZTFile
from dig.processing import dewow, background, gain

# Load a GSSI DZT file using the zero-copy Rust parser
dzt = DZTFile("survey.dzt")
data = dzt.traces

# Apply a standard pipeline
data = dewow.dewow_fft(data, sample_rate=1e9)
data = background.remove_background_global(data)
data = gain.sec_gain(data, sample_rate=1e9)
```

## 🏗️ Architecture

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

## 📊 Supported Formats

| Format | Instrument | Status |
|--------|-----------|--------|
| `.DZT` | GSSI SIR-3000/4000 | ✅ Supported |
| `.DT1`/`.HD` | Sensors & Software Pulse EKKO | ✅ Supported |
| `.dat`/`.grd` | Bartington Grad601 / Geoscan FM256 | ✅ Supported |
| `.sgy` | SEG-Y (interoperability) | ✅ Supported |

## 🛠️ Contributing

We welcome contributions from archaeologists, geophysicists, and software engineers! See our [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on setting up the Rust and Python development environments.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.