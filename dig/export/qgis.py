"""qgis.py — QGIS project file generation (.qgz).

exports: generate_qgz(raster_paths, output_path, project_title, crs_epsg) -> str
used_by: CLI commands, workflows
rules:
  - Generate valid QGIS 3.x project XML structure
  - Layers must have valid singlebandpseudocolor renderer configured
  - Project extent must match raster bounds
"""

import math
from pathlib import Path

import numpy as np
import rasterio


def generate_qgz(
    raster_paths: list[str],
    output_path: str | Path,
    project_title: str = "DIG Geophysical Survey",
    crs_epsg: int = 4326,
) -> str:
    """Generate a QGIS project file (.qgs XML).

    Configures a complete QGIS 3.x project with layer symbology, global extent,
    and proper project tree structuring.

    Args:
        raster_paths: Paths to GeoTIFF files to include
        output_path: Output .qgs path
        project_title: Project title
        crs_epsg: EPSG code for the project CRS

    Returns:
        Path to the written .qgs file
    """
    output_path = Path(output_path)

    xmin, ymin, xmax, ymax = float("inf"), float("inf"), float("-inf"), float("-inf")

    projectlayers_xml = ""
    layertree_xml = ""

    for i, rpath_str in enumerate(raster_paths):
        rpath = Path(rpath_str)
        layer_id = f"dig_layer_{i}"
        layer_name = rpath.stem

        vmin, vmax = 0.0, 255.0

        try:
            with rasterio.open(rpath) as src:
                bounds = src.bounds
                xmin = min(xmin, bounds.left)
                ymin = min(ymin, bounds.bottom)
                xmax = max(xmax, bounds.right)
                ymax = max(ymax, bounds.top)

                band = src.read(1)
                nodata = src.nodata

                if nodata is not None:
                    if np.issubdtype(band.dtype, np.floating) and np.isnan(nodata):
                        valid = band[~np.isnan(band)]
                    else:
                        valid = band[band != nodata]
                else:
                    if np.issubdtype(band.dtype, np.floating):
                        valid = band[~np.isnan(band)]
                    else:
                        valid = band

                if valid.size > 0:
                    vmin = float(np.percentile(valid, 2))
                    vmax = float(np.percentile(valid, 98))
        except Exception:
            pass

        projectlayers_xml += f"""
    <maplayer type="raster" hasScaleBasedVisibilityFlag="0" maxScale="0" minScale="1e+08" autoRefreshTime="0" autoRefreshEnabled="0" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="">
      <id>{layer_id}</id>
      <datasource>{rpath.resolve()}</datasource>
      <layername>{layer_name}</layername>
      <srs>
        <spatialrefsys>
          <authid>EPSG:{crs_epsg}</authid>
        </spatialrefsys>
      </srs>
      <provider>gdal</provider>
      <pipe>
        <rasterrenderer type="singlebandpseudocolor" band="1" alphaBand="-1" classificationMin="{vmin}" classificationMax="{vmax}" opacity="1">
          <rasterTransparency/>
          <minMaxOrigin>
            <limits>MinMax</limits>
            <extent>WholeRaster</extent>
            <statAccuracy>Estimated</statAccuracy>
            <cumulativeCutLower>0.02</cumulativeCutLower>
            <cumulativeCutUpper>0.98</cumulativeCutUpper>
            <stdDevFactor>2</stdDevFactor>
          </minMaxOrigin>
          <rastershader>
            <colorrampshader colorRampType="INTERPOLATED" clip="0" classificationMode="1" maximumValue="{vmax}" minimumValue="{vmin}">
              <colorramp type="gradient" name="[source]">
                <prop k="color1" v="43,131,186,255"/>
                <prop k="color2" v="215,25,28,255"/>
                <prop k="discrete" v="0"/>
                <prop k="rampType" v="gradient"/>
              </colorramp>
              <item alpha="255" value="{vmin}" label="{vmin:.1f}" color="#2b83ba"/>
              <item alpha="255" value="{(vmin + vmax) / 2}" label="{(vmin + vmax) / 2:.1f}" color="#ffffbf"/>
              <item alpha="255" value="{vmax}" label="{vmax:.1f}" color="#d7191c"/>
            </colorrampshader>
          </rastershader>
        </rasterrenderer>
      </pipe>
    </maplayer>"""

        layertree_xml += f"""
    <layer-tree-layer name="{layer_name}" providerKey="gdal" source="{rpath.resolve()}" checked="Qt::Checked" id="{layer_id}" expanded="1">
      <customproperties/>
    </layer-tree-layer>"""

    if math.isinf(xmin):
        xmin, ymin, xmax, ymax = 0, 0, 1000, 1000

    qgs_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.22.0" projectname="{project_title}">
  <title>{project_title}</title>
  <projectlayers>{projectlayers_xml}
  </projectlayers>
  <layer-tree-group>
    <customproperties/>{layertree_xml}
  </layer-tree-group>
  <mapcanvas>
    <units>meters</units>
    <extent>
      <xmin>{xmin}</xmin>
      <ymin>{ymin}</ymin>
      <xmax>{xmax}</xmax>
      <ymax>{ymax}</ymax>
    </extent>
    <projections>
      <crs>
        <spatialrefsys>
          <authid>EPSG:{crs_epsg}</authid>
        </spatialrefsys>
      </crs>
    </projections>
  </mapcanvas>
</qgis>"""

    output_path.write_text(qgs_content)
    return str(output_path)
