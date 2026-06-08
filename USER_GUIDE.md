# DIG User Guide & Manual

Welcome to **DIG (Digital Imaging for Geophysics)**. This application provides field archaeologists and geophysicists with a high-performance environment for importing, processing, and analyzing Ground Penetrating Radar (GPR) and Magnetometry data.

---

## 1. Installation & Setup

### Pre-compiled Standalone Binaries
The easiest way to use DIG is to download the standalone executable for your operating system from the [GitHub Releases](https://github.com/mabo-du/DIG/releases) page.

- **Windows:** Download the `DIG-Windows-Setup.exe` installer. Double-click and follow the wizard.
- **macOS:** Download the `DIG-macOS.dmg` file. Mount it and drag DIG to your Applications folder. *Note on Gatekeeper: If macOS warns that the app is unsigned, right-click the DIG icon and click "Open" to bypass the warning.*
- **Linux:** Download the `DIG-Linux-x86_64.AppImage`. Run `chmod +x DIG-Linux-x86_64.AppImage` to make it executable, then double-click it. *Note: You may need `libxcb-cursor0` installed (`sudo apt-get install libxcb-cursor0`).*

### Python Package (for Developers/Scripters)
If you prefer to use DIG as a Python library:
```bash
pip install dig
```

---

## 2. Importing Data

DIG provides zero-copy, memory-mapped parsers for several proprietary binary formats:
- **GSSI GPR (`.DZT`)**: Contains trace data and internal headers. DIG will also automatically look for and parse `.DZG` sidecar files containing NMEA GPS strings.
- **Sensors & Software PulseEKKO (`.DT1` & `.HD`)**: Requires both files in the same directory. DIG will extract the survey geometry and trace data simultaneously.
- **Bartington / Geoscan Magnetometry (`.dat` & `.grd`)**: Imports zigzag and parallel grid formats, properly masking void values (-32768) as NaNs for processing.
- **SEG-Y (`.sgy`)**: The industry standard for seismic and georadar interoperability.

**To Import:**
1. Open the DIG interface.
2. Click **File -> Import Survey**.
3. Select your raw data files. DIG will automatically detect the instrument type and display the raw radargram (for GPR) or grid (for Magnetometry).

---

## 3. Signal Processing Pipeline

DIG utilizes an immutable, DAG-based (Directed Acyclic Graph) processing pipeline. This means you can apply a chain of filters, and DIG will preserve your original data. You can "branch" off of any step in history to try a different filter.

### GPR Processing Workflow
A typical Ground Penetrating Radar processing sequence includes:

1. **Time-Zero Correction:** Aligns all traces so the surface reflection occurs at $t = 0$. Use the Threshold method or First-Peak method.
2. **De-Wow Filter:** Removes low-frequency induction drift. DIG uses a Fast-Fourier Transform (FFT) high-pass filter for this, which is significantly faster than traditional running means.
3. **Background Removal:** Removes horizontal banding (ringing) caused by antenna crosstalk. Choose between a Global average subtraction or a Localized moving average.
4. **Bandpass Filter:** Eliminates high-frequency noise and low-frequency drift. Configure your low-cut and high-cut frequencies based on your antenna's center frequency.
5. **Gain:** Corrects for the exponential decay of the radar signal through the ground.
   - *SEC (Spherical and Exponential Compensation)*: Mathematically reconstructs the lost amplitude.
   - *AGC (Automatic Gain Control)*: Equalizes the visual appearance of deep and shallow reflectors (useful for display, but destroys relative amplitude).
6. **Migration (Stolt or Kirchhoff):** Collapses hyperbolic diffraction hyperbolas back to their true point sources. This requires estimating the subsurface radar wave velocity first!

### Magnetometry Processing Workflow
1. **Despike:** Removes sudden, sharp spikes caused by modern ferrous trash (like nails or wire).
2. **Destagger:** Corrects for zigzag walking errors where alternating profiles are shifted due to the operator's swing.
3. **Zero Mean Traverse (Destripe):** Removes directional heading errors and sensor drift by balancing the mean of each traverse.

---

## 4. 2D and 3D Visualization

- **2D Profile View (PyQtGraph):** Displays individual GPR radargrams. Use your mouse scroll wheel to adjust color contrast (gain) visually without permanently altering the data.
- **3D Volume Assembly (PyVista):** If your profiles were collected on a grid or have GPS coordinates, click **Assemble 3D Grid**. DIG will interpolate the data into a 3D block.
- **Slice Navigator:** Once a 3D volume is assembled, use the Z-axis slider to scroll through time/depth slices. High-amplitude anomalies (often walls, floors, or ditches) will appear as bright reflections.

---

## 5. Exporting and GIS Integration

Once you have isolated archaeological features:
1. **Export Time Slice:** In the 3D view, select the depth of interest and click **Export -> GeoTIFF**.
2. **Coordinate Reference System (CRS):** DIG will prompt you for an EPSG code (e.g., `EPSG:32632` for UTM Zone 32N). The exported GeoTIFF will be correctly rotated and georeferenced.
3. **QGIS Integration:** Click **Export -> QGIS Project**. DIG will generate a `.qgs` file containing your GeoTIFFs, styled appropriately for archaeological interpretation. You can open this file directly in QGIS.
