# QGIS Integration

[QGIS](https://qgis.org) is a free and open-source Geographic Information System (GIS) used widely in archaeology. DIG is designed to work seamlessly with QGIS.

## Importing DIG Data to QGIS

The easiest way to get your processed maps into QGIS is by using the **GeoTIFF** export format.

1. In DIG, go to **Export** and choose **GeoTIFF**. Ensure you have set the correct Coordinate Reference System (CRS), such as UTM or British National Grid (EPSG:27700).
2. Open QGIS.
3. Drag and drop the `.tif` file from your computer directly into the QGIS map canvas, or use `Layer -> Add Layer -> Add Raster Layer`.
4. QGIS will automatically place the image in the correct real-world location.

## Styling in QGIS

By default, QGIS might display the data as a simple black-and-white gradient. To improve the visualization:
1. Right-click the layer in the QGIS Layers panel and select **Properties**.
2. Go to the **Symbology** tab.
3. Change the Render type to **Singleband pseudocolor**.
4. Choose a color ramp (like a black-to-white or greyscale ramp) and adjust the Min and Max values to match the clipping you used in DIG.
5. Click **Apply**.
