# Processing Reference

This is a technical reference for the algorithms and filters available in DIG's processing pipeline.

## Destriping Filters

### Zero Mean Traverse (ZMT)
Calculates the mean value of each individual traverse (survey line) and subtracts it from every data point in that traverse. This forces the mean of every traverse to be zero.
- **Parameters:** `Threshold` (optional, calculates the mean using only values within the threshold to ignore large spikes).

### Zero Mean Grid (ZMG)
Similar to ZMT, but calculates the mean for an entire grid rather than individual traverses. Useful for matching adjacent survey grids.

## Smoothing & Enhancing

### Despike
Locates data points that differ from their immediate neighbors by a defined threshold and replaces them with a local average.
- **Parameters:** `Window Size` (X and Y radius), `Threshold`.

### Low Pass Filter
Applies a rolling average across the data. This smooths out high-frequency noise but can blur sharp features.
- **Parameters:** `Window Size` (X and Y radius).

### High Pass Filter
Removes broad, slowly changing background trends (like geological changes) to enhance small, localized anomalies.
- **Parameters:** `Window Size` (X and Y radius).

## Geometric Corrections

### De-stagger
Shifts alternating traverses by a specified number of data points or a fraction of a meter. This corrects for operators starting their walking pace at slightly different times on zig-zag surveys.
- **Parameters:** `Shift distance` (positive or negative).
