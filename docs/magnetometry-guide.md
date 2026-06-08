# Magnetometry Guide

Magnetometry is one of the most common geophysical techniques used in archaeology. This guide covers how to get the best results from your magnetic data using DIG.

## Understanding Magnetic Data
Magnetometers measure small variations in the Earth's magnetic field caused by buried features. Fired clay (like hearths or kilns), brick walls, and filled-in ditches all have distinct magnetic signatures.

## Recommended Workflow

1. **Clip Data:** Often, very strong signals from modern metal (like horseshoes or nails) can wash out the subtle signals from archaeology. Clipping the data to a range of -10 to +10 nT is usually a good starting point.
2. **Zero Mean Traverse (ZMT):** Magnetometry data is often collected by walking back and forth in a zig-zag pattern. This can create a striped look. The ZMT filter removes this striping.
3. **De-stagger:** If you walked slightly faster in one direction than the other, features might look jagged. The de-stagger tool nudges the data lines to align them properly.

## Interpreting the Map
- **Dark areas** typically indicate strong positive magnetic signals (e.g., kilns, hearths, iron).
- **Light areas** typically indicate strong negative signals.
- **Dipole anomalies** (a dark spot right next to a light spot) usually mean buried iron objects.
