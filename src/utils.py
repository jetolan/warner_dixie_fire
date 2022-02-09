import rasterio
import numpy as np
from rasterio.warp import reproject, Resampling, calculate_default_transform
import rasterio.mask


def geotiff_to_utm(in_file, out_file, dst_crs, resolution=None, resampling=Resampling.bilinear):
    with rasterio.open(in_file) as src:
        meta = src.meta
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds,
            resolution=resolution)
        meta.update({
            'driver': 'GTiff',
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })
        with rasterio.open(out_file, 'w', **meta) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=resampling)
    return out_file


def crop_to_aoi(in_file, aoi, out_file, nodata=np.NaN):
    with rasterio.open(in_file, 'r') as src:
        arr, trans = rasterio.mask.mask(src, aoi, nodata=nodata, crop=True)
        meta = src.meta
        meta.update({
            "driver": "GTiff",
            "height": arr.shape[1],
            "width": arr.shape[2],
            'transform': trans,
        })

        with rasterio.open(out_file, 'w', **meta) as dst:
            dst.write(arr)

    return out_file
