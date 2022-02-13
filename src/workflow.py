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
    naip_file = f'{figdir}/naip.tif'
    if not os.path.exists(naip_file):
        naip_file = naip.get_masked_raster(
            sch, masked_file=naip_file)
    else:
        print(f"{naip_file} exists, skipping creation...")

    # plotting
    # ------------------------------
    area_km2 = (sch_utm.area/1e6).iloc[0]
    if area_km2 > 10:
        intv, cont, linethick, cfont = 50, 10, 0.25, 2
    elif area_km2 > 0.1 and area_km2 <= 10:
        intv, cont, linethick, cfont = 20, 4, 0.25, 4
    else:
        intv, cont, linethick, cfont = 10, 1, 1, 5

    plotting.plot_contour(demfile, sch_utm, figdir,
                          intv=intv, cont=cont, linethick=linethick, cfont=cfont)
    plotting.plot_hill(hillshade_file, sch_utm, figdir)
    plotting.plot_slope(slope_file, sch_utm, figdir)
    plotting.plot_ba(ba_utm_crop_upsample, sch_utm, figdir)
    plotting.plot_naip(naip_file, sch_utm, figdir)

    _, cell_text = plotting.plot_regen(slope_file, ba_utm_crop_upsample,
                                       naip_file, sch_utm, figdir)

    # collect in document
    # document.make_document(figdir)

    # return dict of values
    all_75 = cell_text[0][3]+cell_text[1][3]+cell_text[2][3]

    sub = pd.DataFrame({'APN': sch.Name.iloc[0],
                        'BA>75 All Slopes': all_75,
                        'BA>75 & S>30': cell_text[0][3],
                        'BA>75 & 30>S>15': cell_text[1][3],
                        'BA>75 & S<15': cell_text[2][3],
                        'BA<75,BA>50  and S>30': cell_text[0][2],
                        'BA<75,BA>50  and 30>S>15': cell_text[1][2],
                        'BA<75,BA>50 and S<15': cell_text[2][2],
                        'BA<50,BA>25 and S>30': cell_text[0][1],
                        'BA<50,BA>25 and 30>S>15': cell_text[1][1],
                        'BA<50,BA>25 and S<15': cell_text[2][1],
                        'BA<25 and S>30': cell_text[0][0],
                        'BA<25 and 30>S>15': cell_text[1][0],
                        'BA<25 and S<15': cell_text[2][0],
                        'geometry': sch.geometry.iloc[0],
                        }, index=[sch.Name.iloc[0]]
                       )
    return sub


if __name__ == "__main__":

    parcel_file = '../data/plumas_parsels.geojson'
    # warner_valley_file = "../data/warner_valley_bounds.geojson"
    warner_valley_file = "../data/warner_watershed.geojson"

    # ---------------------------------
    gdf = gp.read_file(parcel_file)
    val = gp.read_file(warner_valley_file)
    val_gdf = gp.sjoin(gdf, val, how='inner', op='intersects')
    val['Name'] = 'Warner_Watershed'
    val_gdf = pd.concat([val, val_gdf])
    val_gdf.crs = 'epsg:4326'
    apns = val_gdf.Name.to_list()

    # 'Tolanda'
    # apns = ['011180013']

    # 'Williams'
    # apns = ['011180014']

    # 'Farmers'
    # apns = ['011130013']

    # all watershed
    # apns = ['Warner_Watershed']

    for ii, apn in enumerate(apns):
        print(f'Processing {apn}')
        sch = val_gdf[val_gdf['Name'] == apn]
        try:
            sub = process_apn(sch)
            if ii == 0:
                df = sub
            else:
                df = pd.concat([df, sub])
        except Exception as e:
            print(e)

    table.to_table(df)
    folium_map.warner(val_gdf)
