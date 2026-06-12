# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2026-06-12
### Fixed
- **UI:** Resolved layout variable shadowing bugs in `VelocityPanel`, `SliceNavigator`, and `VolumeWidget`.
- **UI:** Fixed Qt enumeration and out-of-bounds indexing bugs in interactive widgets.
- **Core:** Added missing generic type bindings (`Union[DZTFile, DT1File]`) to resolve typing mismatches in batch processing.
- **Core:** Fixed PyInstaller bundled resource path resolution (`sys._MEIPASS`) handling.
- **Rust Backend:** Eliminated `cargo clippy` warnings by appropriately marking unused fields in `DztHeader` and `TraceHeader`.
- **Rust Backend:** Removed dead memory-mapped `MemmapFile` code.
- **Rust Backend:** Simplified Rust-side type complexity (`DzgpResult`) and fixed manual char/math operations to leverage standard library equivalents.

## [0.1.0] - 2026-06-09
### Added
- **Core Architecture:** PyO3/Rust backend (`dig-core`) combined with a Python PySide6/PyVista frontend.
- **Parsers:** Zero-copy, memory-mapped Rust parsers for GSSI `.DZT`, Sensors & Software `.DT1`/`.HD`, and Bartington `.dat`/`.grd` magnetometry data.
- **Signal Processing:** Immutable DAG-based processing pipeline with reproducible audit trails. Includes De-wow, Background Removal, Bandpass filtering, SEC/AGC gain, and Topographic correction.
- **Migration:** High-performance Kirchhoff and Stolt migration implemented in Rust using parallel iterators.
- **Visualization:** PyVista-based 3D grid assembly and slicing, with PyQtGraph 2D profiles and interactive DAG history.
- **Exporting:** Multi-band rotated GeoTIFF export and QGIS `.qgs` project file generation for seamless GIS integration.
- **Packaging:** PyInstaller hooks for macOS `.dmg`, Windows Inno Setup `.exe`, and Linux `AppImage` standalone executables.
- **Documentation:** Full MkDocs site with user guides, tutorials, and `mkdocstrings` API reference.
