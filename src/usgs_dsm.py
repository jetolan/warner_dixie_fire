import numpy as np
import json
import os
import geopandas as gp
import rasterio
from matplotlib.colors import LightSource
from pyproj import Transformer, Proj
import utils as reutil
import tempfile
import urllib.request
import rasterio.windows
from rasterio.transform import Affine

#ll_proj = Proj('epsg:4326')
#dep_proj = Proj('epsg:3857')
#ll_to_dep_trans = Transformer.from_proj(ll_proj, dep_proj)

"""
STEPS:
1.Grab DEM
2.extract slope using np.gradient with a sample length of 10m(?)
"""


def parse_bbox(bbox):
    bbox_str = f'{bbox[0]}%2C+{bbox[1]}%2C+{bbox[2]}%2C+{bbox[3]}'
    size_str = f'{int(bbox[2]-bbox[0])}%2C{int(bbox[3]-bbox[1])}'
    return bbox_str, size_str


def dsm_url(bbox_3857):
    #bbox_3857 = (ll_to_dep_trans.transform(
    #    bbox[1], bbox[0])+ll_to_dep_trans.transform(bbox[3], bbox[2]))
    bbox_str, size_str = parse_bbox(bbox_3857)
    base_url = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage?"
    bbox_url = f"&bbox={bbox_str}"
    size_url = f"&size={size_str}"
    tail_url = "&format=tiff&pixelType=F32&noDataInterpretation=esriNoDataMatchAny&interpolation=+RSP_BilinearInterpolation&renderingRule=rasterFunction%3AIdentity&f=image"
    return f"{base_url}{bbox_url}{size_url}{tail_url}"


def block_shapes(width, height, rows, cols):
    """Generator for windows for optimal reading and writing based on the raster
    format Windows are returns as a tuple with xoff, yoff, width, height.
    
    Parameters
    ----------
    rows : int
        Height of window in rows.
    
    cols : int
        Width of window in columns.
    """

    for i in range(0, width, rows):
        if i + rows < width:
            num_cols = rows
        else:
            num_cols = width - i

        for j in range(0, height, cols):
            if j + cols < height:
                num_rows = rows
            else:
                num_rows = height - j
                
            yield rasterio.windows.Window(i, j, num_cols, num_rows)


def get_dsm_tiff(sch_buf, outfile, dst_crs, overwrite=False):
    """
    Get the dsm tiff from the web

    Params:
    sch_buf: geopandas df with crs specified
    """
    
    if os.path.exists(outfile) and not overwrite:
        print(f'{outfile} exists...skiping download')
        return outfile

    sch_buf_3857 = sch_buf.to_crs('epsg:3857')
    
    # if the area is too big, downsample raster
    if (sch_buf_3857.area/1e6).iloc[0] > 10:
        res = 2
    else:
        res = None

    bbox = sch_buf_3857.geometry.unary_union.bounds
    width = int(bbox[2]-bbox[0])
    height = int(bbox[3]-bbox[1])
    transform = rasterio.transform.from_bounds(*bbox, width, height)
    windows = block_shapes(width, height, 2048, 2048)

    meta={'driver': 'GTiff',
          'crs': 'epsg:3857',
          'transform': transform,
          'width': width,
          'height': height,
          'count': 1,
          'dtype': 'float32',
          
        }
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=True) as tmp:
        with rasterio.open(tmp, 'w', **meta) as dst:
            for window in windows:
                bbox = rasterio.windows.bounds(window, transform)
                dem_str = dsm_url(bbox)
                with tempfile.NamedTemporaryFile(suffix='.tif', delete=True) as tmp_block:
                    urllib.request.urlretrieve(dem_str, tmp_block.name)
                    with rasterio.open(tmp_block.name) as src:
                        block = src.read(1)
                dst.write_band(1, block,window=window)

        #reproject and resample
        reutil.geotiff_to_utm(
            tmp.name, outfile, dst_crs, resolution=res)
                    
    return outfile


def dsm_products(outfile, hillshade=True, slope=True):
    # read the dsm tiff and create products
    ##########################
    with rasterio.open(outfile, 'r') as src:
        data = src.read(1)
        meta = src.meta
        bounds = src.bounds
        res = src.res

        # save hillshade tiff
        if hillshade:
            ls = LightSource(azdeg=315, altdeg=45)
            hill = ls.hillshade(data, vert_exag=1)
            hillshade_file = outfile.replace('.tif', '_hillshade.tif')
            with rasterio.open(hillshade_file, 'w', **meta) as dst:
                dst.write(hill.astype(meta['dtype']), 1)

        # save the slope tiff
        if slope:
            gradient = np.gradient(data)
            slope = np.sqrt(gradient[0]**2++gradient[1]**2)*(1/np.mean(res))
            slope_deg = np.arctan(slope)*180/np.pi
            slope_file = outfile.replace('.tif', '_slope.tif')
            with rasterio.open(slope_file, 'w', **meta) as dst:
                dst.write(slope_deg, 1)

        return hillshade_file, slope_file


if __name__ == "__main__":

    parcel_file = '../data/plumas_parsels.geojson'
    name = 'Tolanda'
    apn = '011180013'
    gdf = gp.read_file(parcel_file)
    sch = gdf[gdf['Name'] == apn]
    #get_dsm_tiff(sch, outfile='test.tif', dst_crs="epsg:32610")

    warner_valley_file = "../data/warner_valley_bounds.geojson"
    warner_valley_file = "../data/warner_watershed.geojson"
    val = gp.read_file(warner_valley_file)
    val.to_crs('epsg:4326')
    get_dsm_tiff(val, outfile='test.tif', dst_crs="epsg:32610")

    """
    val_gdf = gp.sjoin(gdf, val, how='inner', op='within')
    sch = gp.GeoDataFrame({'Name': 'All_Valley'},
                          geometry=[val_gdf.unary_union], index=[0], crs='epsg:4326')
    get_dsm_tiff(sch, outfile='dem.tif', dst_crs="epsg:32610")
    """
