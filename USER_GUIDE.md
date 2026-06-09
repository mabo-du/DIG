# DIG (Digital Imaging for Geophysics) - User Guide

Welcome to **DIG**, an open-source, high-performance desktop application for processing, visualizing, and exporting Ground Penetrating Radar (GPR) and Magnetometry survey data.

Unlike traditional geophysical software that forces destructive changes onto your raw data, DIG uses a non-destructive, DAG-based (Directed Acyclic Graph) pipeline. Your original data is never modified, and you can instantly step back through your processing history, branch off to try different filters, or compare the results of different gain algorithms side-by-side.

---

## 1. Getting Started

### 1.1 Launching the Application
Once installed via the standalone executables (or via `python -m dig`), the main window will appear. The interface is composed of multiple dockable panels surrounding a central visualization area.
- **Center:** The Radargram (2D) or Volume (3D) viewer.
- **Left Panel:** History and Processing Pipeline.
- **Right Panel:** Display Controls and Filter Parameters.
- **Bottom Panel:** Depth/Time Slice Navigator (active in 3D mode).

### 1.2 Importing Raw Data
To load a survey:
1. Go to **File -> Open Profile** (or press `Ctrl+O`).
2. Select your raw binary file:
   - **GSSI (`.DZT`)**: Contains trace data. DIG automatically seeks `.DZG` sidecars for GPS coordinates.
   - **Sensors & Software (`.DT1`)**: Standard PulseEKKO format. DIG also requires the `.HD` header file to be in the same folder.
3. Once loaded, the 2D Radargram view will populate immediately.

---

## 2. Navigating the Interface

### 2.1 The Radargram Viewer (2D)
The central 2D viewer plots distance (or trace number) along the X-axis and time (nanoseconds) along the Y-axis. 
- **Pan:** Click and drag the middle mouse button.
- **Zoom:** Scroll the mouse wheel, or right-click and drag to define a zoom rectangle.
- **Measure:** Hovering over the plot displays the current X,Y coordinates and amplitude value in the status bar.

### 2.2 Display Controls (Right Panel)
The right panel dictates *how* the data is drawn, without altering the underlying numbers.
- **Color Map:** Switch between standard geophysical palettes (e.g., Grayscale, Seismic, Turbo).
- **Contrast (Gain):** Adjust the minimum and maximum amplitude thresholds to clamp the visual range. This visually "boosts" faint reflections without changing the math in your pipeline.
- **Interpolation:** Toggle pixel interpolation smoothing on or off.

---

## 3. The Signal Processing Pipeline

The left panel houses the **Processing History**. Every time you apply a filter, a new "Step" is added to the history tree. 

### 3.1 Standard GPR Pipeline
Geophysical data generally requires a sequence of filters to become interpretable. A recommended standard workflow in DIG:

1. **Time Zero Correction**
   - *Why:* The radar wave travels through the air before hitting the ground, so the ground surface doesn't start at $t=0$. 
   - *Action:* DIG shifts all traces upward so the first major reflection (the ground wave) aligns at $0$ nanoseconds.
2. **Dewow (Low-Frequency Removal)**
   - *Why:* Inductive coupling near the antenna creates a low-frequency "wow" that distorts the baseline.
   - *Action:* Apply the **FFT Dewow** or **Median Dewow**. The FFT dewow acts as a high-pass filter and is nearly instantaneous.
3. **Background Removal (Spatial Filtering)**
   - *Why:* Horizontal ringing (antenna crosstalk) obcures deeper hyperbolic reflections.
   - *Action:* Apply **Global Background Removal** to subtract the average of all traces from every trace, neutralizing perfectly horizontal bands.
4. **Gain Compensation**
   - *Why:* Radar energy attenuates exponentially as it travels through soil. Deeper reflections are mathematically invisible compared to surface noise.
   - *Action:* Apply **SEC Gain** (Spherical and Exponential Compensation). This applies an exponential multiplier based on depth to scientifically recover lost amplitude. 
   - *Alternative:* **AGC Gain** (Automatic Gain Control) forces all reflections to have equal brightness. Useful for visualization, but destroys relative amplitude information.

### 3.2 Branching Your History
If you reach the end of your pipeline but want to see what the data would look like if you used a different filter earlier:
1. Click on a previous step in the **History Panel**.
2. Apply a new filter. 
3. DIG will split the history into a "Branch," preserving your old pipeline while allowing you to explore the new one.

---

## 4. Subsurface Velocity and Migration

Hyperbolic diffractions occur because the radar beam spreads out in a cone. As the antenna approaches a buried rock or pipe, the reflection appears deeper (the sides of the hyperbola) until the antenna is directly over it (the apex).

To correct this and collapse hyperbolas into their true point sources, you must apply **Migration**.
1. **Estimate Velocity:** Use the **Velocity Panel** to overlay a theoretical hyperbola on your data. Adjust the velocity slider until the theoretical curve perfectly matches a real hyperbola in the ground.
2. **Migrate:** Once you know the soil's dielectric velocity (e.g., $0.1$ m/ns for dry soil), apply **Stolt Migration** or **Kirchhoff Migration**. The hyperbolas will collapse into concentrated dots, indicating the true location of the buried objects.

---

## 5. Volumetric Assembly and Export

### 5.1 The Slice Navigator (3D)
If you have imported multiple parallel profiles (or a grid), DIG can interpolate them into a 3D block.
1. Click **Assemble Grid**.
2. The central viewer switches to the 3D PyVista engine.
3. Use the **Slice Navigator** at the bottom of the screen to drag a horizontal plane down through the Z-axis (time/depth).
4. High-amplitude anomalies visible on these horizontal slices often correspond to walls, floors, or ditches.

### 5.2 Exporting to GIS
Once you have identified an archaeological feature at a specific depth:
1. Navigate to that specific time slice.
2. Click **Export -> GeoTIFF**.
3. You will be prompted to enter your local EPSG coordinate reference code.
4. DIG will export a georeferenced raster image that can be dragged directly into QGIS, ArcGIS, or HOARD for your final archaeological report.
