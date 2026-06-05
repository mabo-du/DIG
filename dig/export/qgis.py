"""QGIS project file generation (.qgz).

Generates a QGIS project with pre-configured layers for processed
geophysical data — no manual setup required.
"""

from pathlib import Path
import json


def generate_qgz(
    raster_paths: list[str],
    output_path: str | Path,
    project_title: str = "DIG Geophysical Survey",
    crs_epsg: int = 4326,
) -> str:
    """Generate a QGIS project file (.qgs XML).

    Note: Full .qgz generation requires the qgis Python bindings.
    This generates a .qgs file that QGIS can open directly.

    Args:
        raster_paths: Paths to GeoTIFF files to include
        output_path: Output .qgs path
        project_title: Project title
        crs_epsg: EPSG code for the project CRS

    Returns:
        Path to the written .qgs file
    """
    output_path = Path(output_path)

    # Build QGIS project XML
    layers_xml = ""
    for i, rpath in enumerate(raster_paths):
        layers_xml += f"""
  <maplayer>
    <id>dig_layer_{i}</id>
    <name>{Path(rpath).stem}</name>
    <type>raster</type>
    <datasource>{rpath}</datasource>
    <layername>{Path(rpath).stem}</layername>
    <provider encoding="UTF-8">gdal</provider>
  </maplayer>"""

    qgs_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="{project_title}">
  <title>{project_title}</title>
  <layer-tree-group>
    <layer-tree-layer name="DIG Survey Data" checked="Qt::Checked" id="dig_group">
      {layers_xml}
    </layer-tree-layer>
  </layer-tree-group>
  <mapcanvas>
    <units>meters</units>
    <extent>
      <xmin>0</xmin>
      <ymin>0</ymin>
      <xmax>1000</xmax>
      <ymax>1000</ymax>
    </extent>
    <projections>
      <crs>
        <spatialrefsys>
          <epsg>{crs_epsg}</epsg>
        </spatialrefsys>
      </crs>
    </projections>
  </mapcanvas>
</qgis>"""

    output_path.write_text(qgs_content)
    return str(output_path)