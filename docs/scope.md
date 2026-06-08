# PROJECT — DIG: Digital Imaging for Geophysics

## Overview
A comprehensive tool for processing, analyzing, and visualizing Ground Penetrating Radar (GPR) and Magnetometry data. It aims to support standard formats from GSSI, Bartington, and others. Current proprietary software is highly expensive and complex.

## Target users
- Geophysical archaeologists surveying unexcavated sites
- Field technicians processing GPR or magnetometry data
- Academic researchers combining geophysical and excavation data

## MVP scope (v1)
- Import GPR formats (.dzt) and Magnetometry formats (.dat)
- Basic signal processing filters (de-wow, background removal, bandpass)
- Time-slice generation from 2D GPR profiles
- Interactive 2D radargram viewer with depth calibration
- Basic 2D grid interpolation for magnetometry data
- Export processed datasets as GeoTIFF or CSV for QGIS
- 3D volume rendering of GPR data
- Advanced velocity analysis and hyperbola fitting
- Automated anomaly detection using machine learning
- Support for more formats (Sensors & Software, Geoscan)

## Tech stack recommendation
- **Language**: Python (for heavy numerical processing)
- **GUI**: PyQt6 or PySide6
- **Processing**: NumPy, SciPy, Pandas
- **Visualization**: Matplotlib, PyQtGraph, PyVista
