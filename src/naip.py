import boto3
import os
import pandas as pd
import rasterio
from rasterio.merge import merge
import json
import pyproj
import numpy as np
import shapely
import shapely.geometry
import numbers
import rtree
import geopandas as gp

import utils as reutil

HOME = os.path.expanduser("~")
NAIP_DIR = f'{HOME}/data//NAIP/'
LOCAL_DIR = '../data/NAIP/'


def project_coords(coords, from_proj, to_proj):
    if len(coords) < 1:
        return []

    if isinstance(coords[0], numbers.Number):
        from_x, from_y = coords[0], coords[1]
        trans = pyproj.Transformer.from_proj(from_proj, to_proj)
        to_x, to_y = trans.transform(from_y, from_x)
        return [to_x, to_y]

    new_coords = []
    for coord in coords:
        new_coords.append(project_coords(coord, from_proj, to_proj))
    return new_coords


def project_feature(feature, from_proj, to_proj):

    if not 'geometry' in feature or not 'coordinates' in feature['geometry']:
        print('Failed project feature', feature)
        return None
    new_coordinates = project_coords(
        feature['geometry']['coordinates'], from_proj, to_proj)
    feature['geometry']['coordinates'] = new_coordinates
    return feature


def download(address, replace=False, download_dir=NAIP_DIR):
    outfile = os.path.join(download_dir, os.path.basename(address))

    if os.path.exists(outfile):
        exists = True
        try:
            src = rasterio.open(outfile)
            corrupt = False
        except(rasterio.errors.RasterioIOError):
            exists = False
            corrupt = True
    else:
        exists = False
        if not exists:
            print("downloading naip file "+outfile)
        elif exists and replace:
            print("downloading naip file "+outfile)
        elif corrupt:
            print("downloading naip file "+outfile)
        else:
            print(outfile + ' exists')

        def get(address, outfile):
            s3_client = boto3.client('s3')
            s3_client.download_file(
                'naip-source', address, outfile, {'RequestPayer': 'requester'})

        get(address, outfile)
    return outfile


def parse_aws_naip_manifest(manifest_file=f'{LOCAL_DIR}/manifest.txt'):
    """
    According to :
    https://docs.opendata.aws/naip/readme.html
    we get the full list of files with
    aws s3 cp s3://naip-source/manifest.txt manifest.txt --request-payer
    """
    df = pd.read_csv(manifest_file, sep='/', header=None,
                     names=['State', 'Year', 'Res', 'Type', 'Quad', 'Filename'])

    df = df[df['Filename'].notna()]

    def get_date(instr):
        base = os.path.splitext(instr)[0]
        date = base[-8:]
        return date
    df['Date'] = df['Filename'].apply(get_date)

    full_path = pd.read_csv(manifest_file, names=['Fullpath'], header=None)
    df = df.merge(full_path, how='outer', left_index=True, right_index=True)

    return df


def sjoin(shape1, shape2):
    tree_idx = rtree.index.Index()
    for i, shp in enumerate(shape1['features']):
        shp_shp = shapely.geometry.shape(shp['geometry'])
        tree_idx.insert(i, (shp_shp.bounds), obj=shp['properties'])
    match = tree_idx.intersection(
        shapely.geometry.shape(shape2[0]['geometry']).bounds, objects=True)
    return [f.object for f in match]


def get_usgs_topo_quad(shape):
    """
    Look at shapefile to get quad
    https://www.arcgis.com/home/item.html?id=4bf2616d2f054fbe92eadcdc9582a765
    """
    usgs_shapefile = os.path.join(LOCAL_DIR, 'usgs_topo_quads.geojson')
    with open(usgs_shapefile) as f:
        usgs_polys = json.load(f)
    usgs_crs = pyproj.crs.CRS(usgs_polys['crs']['properties']['name'])

    # project shape to crs of usgs
    shape_crs = pyproj.crs.CRS(shape['crs']['properties']['name'])
    new_shape = [project_feature(shp, shape_crs, usgs_crs)
                 for shp in shape['features']]
    merged = sjoin(usgs_polys, new_shape)

    def add_quad_num(qd_id):
        qd_id_key = qd_id[-2:]
        alpha_num = {'A': 0, 'B': 1, 'C': 2,
                     'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7}
        # qd_id is grid is 8x8 with A1 in SE naip has 0 at NW (and 1-64)
        qd = qd_id[:-3]
        qd_num = qd+str((64-(alpha_num[qd_id_key[0]]*8) -
                         int(qd_id_key[1])+1)).zfill(2)
        return qd_num
    out = []
    for mm in merged:
        mm['state_abbr'] = state_to_abbr(mm['ST_NAME1'])
        mm['naip_quad_num'] = add_quad_num(mm['USGS_QD_ID'])
        out.append(mm)
    return out


def get_naip_quads(topo_quads, outfile_name=None, replace=False):
    """
    Downloads naip files containing dataframe
    """
    mm = parse_aws_naip_manifest()

    all_dates = ''
    all_quads = ''
    out_files = []

    for ind, row in enumerate(topo_quads):
        if isinstance(row['state_abbr'], str):
            state_abbr = row['state_abbr'].lower()
        else:
            state_abbr = '_'.join([s.lower()
                                   for s in row['state_abbr'].unique()])

        qd_num = row['naip_quad_num']
        qd = qd_num[:-2]

        # now need to use the qd info to find the most recent address
        qd_df = mm[(mm['State'] == state_abbr) & (mm['Quad'] == qd)]
        qd_num_df = qd_df[qd_df.Filename.str.contains(qd_num)]

        qd_rgbir_df = qd_num_df[qd_num_df['Type'] == 'rgbir']
        qd_rgbir = qd_rgbir_df.sort_values('Year', ascending=False)

        # get most recent 4 files
        n_qds = 0
        while n_qds < len(qd_rgbir):
            prev = n_qds
            n_qds += 4
            files = qd_rgbir['Fullpath'].iloc[prev:n_qds].values.tolist()
            dates = np.unique(qd_rgbir['Date'].iloc[prev:n_qds])
            if len(dates) > 1:
                print('Warning:more that one date')
            date = dates[0]
            if any(x in ''.join(files) for x in ['nw', 'ne', 'se', 'sw']):
                break

        all_dates += date+'_'
        all_quads += qd_num+'_'

        for ff in files:
            out_files.append(download(ff, replace=replace))
    str_out = f"{all_quads}_{all_dates}"
    return out_files, str_out


def state_to_abbr(state):
    statename_to_abbr = {
        'Alabama': 'AL',
        'Alaska': 'AK',
        'American Samoa': 'AS',
        'Arizona': 'AZ',
        'Arkansas': 'AR',
        'California': 'CA',
        'Colorado': 'CO',
        'Connecticut': 'CT',
        'Delaware': 'DE',
        'District of Columbia': 'DC',
        'Florida': 'FL',
        'Georgia': 'GA',
        'Guam': 'GU',
        'Hawaii': 'HI',
        'Idaho': 'ID',
        'Illinois': 'IL',
        'Indiana': 'IN',
        'Iowa': 'IA',
        'Kansas': 'KS',
        'Kentucky': 'KY',
        'Louisiana': 'LA',
        'Maine': 'ME',
        'Maryland': 'MD',
        'Massachusetts': 'MA',
        'Michigan': 'MI',
        'Minnesota': 'MN',
        'Mississippi': 'MS',
        'Missouri': 'MO',
        'Montana': 'MT',
        'Nebraska': 'NE',
        'Nevada': 'NV',
        'New Hampshire': 'NH',
        'New Jersey': 'NJ',
        'New Mexico': 'NM',
        'New York': 'NY',
        'North Carolina': 'NC',
        'North Dakota': 'ND',
        'Northern Mariana Islands': 'MP',
        'Ohio': 'OH',
        'Oklahoma': 'OK',
        'Oregon': 'OR',
        'Pennsylvania': 'PA',
        'Puerto Rico': 'PR',
        'Rhode Island': 'RI',
        'South Carolina': 'SC',
        'South Dakota': 'SD',
        'Tennessee': 'TN',
        'Texas': 'TX',
        'Utah': 'UT',
        'Vermont': 'VT',
        'Virgin Islands': 'VI',
        'Virginia': 'VA',
        'Washington': 'WA',
        'West Virginia': 'WV',
        'Wisconsin': 'WI',
        'Wyoming': 'WY'
    }

    return statename_to_abbr[state.title()]


def shape_to_geojson(shapes, crs):
    features = []
    for shape in shapes:
        features.append({'type': 'Feature', 'properties': {},
                         'geometry': shapely.geometry.mapping(shape)})
    out = {'features': features, 'crs': {'properties': {'name': crs}}}
    return out


def merge_rasters(files, outfile='test.tiff'):

    src_files_to_mosaic = []
    for fp in files:
        src = rasterio.open(fp)
        src_files_to_mosaic.append(src)

    crs = src.crs
    out_meta = src.meta.copy()
    mosaic, out_trans = merge(src_files_to_mosaic)

    # Update the metadata
    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans,
                     "crs": crs})

    with rasterio.open(outfile, "w", **out_meta) as dest:
        dest.write(mosaic)
    return outfile


def get_raster(gdf, check_utm=False):
    files_out = []
    for i, row in gdf.iterrows():
        shapes = [row.geometry]
        geojson = shape_to_geojson(shapes, crs='epsg:4326')
        topo_quads = get_usgs_topo_quad(geojson)
        files, str_out = get_naip_quads(topo_quads)
        merge_file = f"{os.path.dirname(files[0])}/{str_out}.tif"
        utm_file = merge_file.replace('.tif', '_utm.tif')
        if check_utm and os.path.exists(utm_file):
            print('utm_file exists, skipping creation of merge file')
        elif not os.path.exists(merge_file):
            merge_rasters(files, merge_file)
        files_out.append(merge_file)
    return files_out


def get_masked_raster(gdf, dst_crs="epsg:32610", masked_file=None):
    filename = get_raster(gdf, check_utm=True)[0]
    file_utm = filename.replace('.tif', '_utm.tif')
    gdf_utm = gdf.to_crs(dst_crs)
    poly_utm = gdf_utm.unary_union
    if not os.path.exists(file_utm):
        reutil.geotiff_to_utm(filename, file_utm, dst_crs)
    masked_file = masked_file or filename.replace('.tif', '_masked.tif')
    reutil.crop_to_aoi(file_utm, [poly_utm], masked_file, nodata=0)
    return masked_file


if __name__ == "__main__":

    lat = 37.47085
    lon = -122.1935922
    lat = 47.60995713411172
    lon = -122.33602664031982
    gdf = gp.GeoDataFrame(
        geometry=[shapely.geometry.Point(lon, lat).buffer(0.01)], crs='epsg:4326')
    naip_file = get_masked_raster(gdf)
