import os
import pandas as pd
import geopandas as gp
import rasterio
from rasterio.warp import Resampling

import usgs_dsm
import naip
import plotting
import utils as reutil
import document
import table
import folium_map

BA_FILE = "../data/ca3987612137920210714_20201012_20211015_ravg_data/ca3987612137920210714_20201012_20211015_rdnbr_ba.tif"
DST_CRS = "epsg:32610"


def process_apn(sch):

    # processing for this APN parcel
    tempdir = '../data/tmp/'
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    figdir = f'../fig/{sch.Name.iloc[0]}'
    if not os.path.exists(figdir):
        os.makedirs(figdir)

    sch_utm = sch.to_crs(DST_CRS)
    sch_utm_buf = sch_utm.buffer(15)
    sch_buf = sch_utm_buf.to_crs('epsg:4326')

    # dem
    demfile = f'{figdir}/dem.tif'
    demfile = usgs_dsm.get_dsm_tiff(sch_buf, demfile, dst_crs=DST_CRS)
    hillshade_file, slope_file = usgs_dsm.dsm_products(demfile)

    # ba
    ba_filename = os.path.basename(BA_FILE)
    ba_utm = f"{tempdir}{ba_filename.replace('.tif', '_utm.tif')}"
    ba_utm = reutil.geotiff_to_utm(BA_FILE, ba_utm, dst_crs=DST_CRS)
    ba_utm_crop = ba_utm.replace('.tif', '_crop.tif')
    sch_utm_buf_large = sch_utm.buffer(30)
    ba_utm_crop = reutil.crop_to_aoi(ba_utm, sch_utm_buf_large, ba_utm_crop)
    ba_utm_crop_upsample = ba_utm_crop.replace('.tif', '_resample.tif')
    with rasterio.open(demfile) as src:
        res = src.res
    reutil.geotiff_to_utm(ba_utm_crop, ba_utm_crop_upsample, dst_crs=DST_CRS,
                          resolution=res, resampling=Resampling.nearest)

    # naip
    naip_filename = naip.get_masked_raster(sch)

    # plotting
    # ------------------------------
    plotting.plot_contour(demfile, sch_utm, figdir)
    # plotting.plot_hill(hillshade_file, sch_utm, figdir)
    plotting.plot_slope(slope_file, sch_utm, figdir)
    plotting.plot_ba(ba_utm_crop_upsample, sch_utm, figdir)
    plotting.plot_naip(naip_filename, figdir)
    _, cell_text = plotting.plot_regen(slope_file, ba_utm_crop_upsample,
                                       naip_filename, sch_utm, figdir)

    # collect in document
    document.make_document(figdir)

    # return dict of values
    all_75 = cell_text[0][3]+cell_text[1][3]+cell_text[2][3]
    low75 = cell_text[2][3]
    sub = pd.DataFrame({'APN': sch.Name.iloc[0],
                        'BA>75%': all_75,
                        'BA>75%,SLOPE<15%': low75,
                        'geometry': sch.geometry.iloc[0],
                        }, index=[sch.Name.iloc[0]])
    return sub


if __name__ == "__main__":

    parcel_file = '../data/plumas_parsels.geojson'
    warner_valley_file = "../data/warner_valley_bounds.geojson"

    # ---------------------------------
    gdf = gp.read_file(parcel_file)
    val = gp.read_file(warner_valley_file)
    val_gdf = gp.sjoin(gdf, val, how='inner', op='within')
    val['Name'] = 'All_Valley'
    val_gdf = pd.concat([val, val_gdf])
    apns = val_gdf.Name.to_list()

    # name = 'Tolanda'
    # apns = ['011180013']

    # name = 'Williams'
    # apns = ['011180014']

    # name = 'Farmers'
    # apns = ['011130013']

    for ii, apn in enumerate(apns[1:]):
        print(f'Processing {apn}')
        sch = val_gdf[val_gdf['Name'] == apn]
        try:
            sub = process_apn(sch)
            if ii == 0:
                df = sub
            else:
                df = pd.concat([df, sub])
        except Exception as e:
            print(e.message)

    table.to_table(df)
    folium_map.warner(df)