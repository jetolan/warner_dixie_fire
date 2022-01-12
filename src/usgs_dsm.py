import numpy as np
import requests
import json
import os
import geopandas as gp
import rasterio
from matplotlib.colors import LightSource
from pyproj import Transformer, Proj
import utils as reutil

ll_proj = Proj('epsg:4326')
dep_proj = Proj('epsg:3857')
ll_to_dep_trans = Transformer.from_proj(ll_proj, dep_proj)

"""
STEPS:
1.Grab DEM
2.extract slope using np.gradient with a sample length of 10m(?)
"""


def parse_bbox(bbox):
    bbox_str = f'{bbox[0]}%2C+{bbox[1]}%2C+{bbox[2]}%2C+{bbox[3]}'
    size_str = f'{int(bbox[2]-bbox[0])}%2C{int(bbox[3]-bbox[1])}'
    return bbox_str, size_str


def dsm_url(bbox):
    bbox_3857 = (ll_to_dep_trans.transform(
        bbox[1], bbox[0])+ll_to_dep_trans.transform(bbox[3], bbox[2]))
    bbox_str, size_str = parse_bbox(bbox_3857)
    base_url = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage?"
    bbox_url = f"&bbox={bbox_str}"
    size_url = f"&size={size_str}"
    tail_url = "&format=tiff&pixelType=F32&noDataInterpretation=esriNoDataMatchAny&interpolation=+RSP_BilinearInterpolation&renderingRule=rasterFunction%3AIdentity&f=image"
    return f"{base_url}{bbox_url}{size_url}{tail_url}"


def get_dsm_tiff(sch_buf, outfile, dst_crs, overwrite=False):

    if os.path.exists(outfile) and not overwrite:
        return outfile

    # get the dsm tiff from the web
    ######################
    bbox = sch_buf.geometry.unary_union.bounds
    dem_str = dsm_url(bbox)
    outfile = reutil.geotiff_to_utm(dem_str, outfile, dst_crs)
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
                dst.write(hill, 1)

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
    val = gp.read_file(warner_valley_file)
    #get_dsm_tiff(val, outfile='test.tif', dst_crs="epsg:32610")

    val_gdf = gp.sjoin(gdf, val, how='inner', op='within')
    sch = gp.GeoDataFrame({'Name': 'All_Valley'},
                          geometry=[val_gdf.unary_union], index=[0])
    get_dsm_tiff(sch, outfile='dem.tif', dst_crs="epsg:32610")
