import os
import pandas as pd
import geopandas as gp
import numpy as np
import folium
import utils
import rasterio
import pyproj
from shapely.geometry import box
import matplotlib.cm as cm


def warner(gdf):
    m = folium.Map(location=[40.419097, -121.330998],
                   zoom_start=14, tiles='CartoDB positron')
    tiles = folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr='Google',
        name='Google Satellite',
        overlay='False',
        control='True',
        opacity=1,
    ).add_to(m)

    for _, r in gdf.iterrows():
        sim_geo = gp.GeoSeries(r['geometry'])  # .simplify(tolerance=0.001)
        geo_j = sim_geo.to_json()
        geo_j = folium.GeoJson(data=geo_j,
                               style_function=lambda x: {'fillColor': 'white'})

        folium.Popup(
            f"<a href = 'doc/{r.APN}.pdf'> {r.APN}</a>").add_to(geo_j)
        geo_j.add_to(m)

    ba_file = "../data/ca3987612137920210714_20201012_20211015_ravg_data/ca3987612137920210714_20201012_20211015_rdnbr_ba.tif"
    mer_file = f"/tmp/{os.path.basename(ba_file)}"
    web_crs = "epsg:3857"
    utils.geotiff_to_utm(ba_file, mer_file, dst_crs=web_crs)
    crop_file = mer_file.replace('.tif', '_projected.tif')
    aoi = gdf[gdf['APN'] == 'All_Valley']
    aoi = aoi.to_crs(web_crs)
    utils.crop_to_aoi(
        mer_file, [box(*aoi.iloc[0].geometry.buffer(10000).bounds)], crop_file, nodata=255)
    with rasterio.open(crop_file) as src:
        dataimage = src.read(1)/255
        bounds = src.bounds
    proj = pyproj.Transformer.from_crs(3857, 4326, always_xy=True)
    xmin, ymin = proj.transform(bounds[0], bounds[1])
    xmax, ymax = proj.transform(bounds[2], bounds[3])

    folium.raster_layers.ImageOverlay(
        image=dataimage,
        bounds=[[ymin, xmin], [ymax, xmax]],
        opacity=0.6,
        colormap=cm.get_cmap('hot'),
    ).add_to(m)
    m.save('../map.html')


if __name__ == "__main__":
    parcel_file = '../data/plumas_parsels.geojson'
    warner_valley_file = "../data/warner_valley_bounds.geojson"
    gdf = gp.read_file(parcel_file)
    val = gp.read_file(warner_valley_file)
    val_gdf = gp.sjoin(gdf, val, how='inner', op='within')
    all_valley = gp.GeoDataFrame({'Name': 'All_Valley'}, geometry=[
        val_gdf.unary_union], crs=val.crs, index=[0])
    val_gdf = pd.concat([all_valley, val_gdf])
    val_gdf['APN'] = val_gdf['Name']
    warner(val_gdf)