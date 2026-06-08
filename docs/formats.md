# Formats Reference

This document provides a technical overview of the file formats supported by DIG. 

## Import Formats

| Format | Extension | Description | Notes |
|---|---|---|---|
| Geoscan Research | `.xyz` | Standard text output from Geoscan instruments. | Make sure dummy values are set correctly during import. |
| Bartington | `.dat` / `.xml` | Native output from Bartington Grad601/Data Logger. | Automatically parses grid dimensions from XML headers. |
| Sensors & Software | `.dt1` / `.hd` | Standard GPR format. | Both the header (.hd) and data (.dt1) files must be in the same directory. |

## Export Formats

### GeoTIFF (`.tif`)
GeoTIFF is the standard for raster data in GIS. DIG exports a single-band 32-bit floating-point GeoTIFF. Georeferencing information (bounding box and CRS) is embedded directly into the file metadata.

### GeoJSON (`.geojson`)
Useful for vectorizing anomalies. DIG can export bounded polygons representing regions that fall above or below a specified threshold.

### CSV (`.csv`)
The CSV export provides a simple tabular format: `X, Y, Value`. 
- `X` and `Y` represent geographic coordinates if the grid is georeferenced.
- `Value` is the processed reading at that location.
