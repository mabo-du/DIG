# Hoard Integration

[HOARD](https://github.com/mabo-du/HOARD) (Heritage Object and Artifact Research Database) is a database system often used for cataloging small finds and bulk artifacts. While geophysical data doesn't directly map to individual artifacts, you can correlate metal detector survey results with your Hoard catalog.

## Workflow

1. If you conducted a metal detector survey and logged the GPS coordinates of hits, import this data into DIG as a point cloud.
2. Export the point data as a **CSV** file.
3. In Hoard, use the **Batch Spatial Import** tool and map the X and Y columns from your CSV to the spatial coordinates in the database.
4. This allows you to visualize the density of metal hits alongside your structural geophysics in GIS or within the Hoard interface.
