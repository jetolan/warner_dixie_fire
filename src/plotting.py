import numpy as np
import rasterio
import rasterio.plot
import rasterio.mask
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
from matplotlib.gridspec import GridSpec


METERS_IN_FT = .3048
M2_IN_ACRE = 4046.86


def plot_contour(outfile, aoi, figdir, meters=False):
    # contour figure
    with rasterio.open(outfile, 'r') as src:
        data = src.read(1)
        meta = src.meta
        bounds = src.bounds
        res = src.res

    xxx = np.linspace(bounds[0], bounds[2], meta['width'])
    yyy = np.linspace(bounds[1], bounds[3], meta['height'])

    # crop interpolated area off
    crop = 4  # pixels
    xxx = xxx[crop:-crop]
    yyy = yyy[crop:-crop]
    data = data[crop:-crop, crop:-crop]

    yyy = np.flip(yyy)
    X, Y = np.meshgrid(xxx, yyy)

    if meters:
        z = data
        cont = 0.5
        intv = 5

    else:
        z = data/METERS_IN_FT
        cont = 1
        intv = 10

    lowm = np.floor(np.min(z))
    highm = np.ceil(np.max(z))
    levels = np.arange(lowm-lowm % intv, highm, cont)
    thick = np.ones(len(levels))/2
    thick[np.squeeze((np.argwhere(levels % intv == 0)))] = 1
    labels = np.arange(lowm-lowm % intv, highm, intv).astype(int)

    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches((12, 12))
    contours = plt.contour(
        X, Y, z, levels, colors='black', linewidths=thick)
    plt.clabel(contours, labels, inline=1, fontsize=5, fmt='%1.0f')
    plt.xlabel('East')
    plt.ylabel('North')
    # add prop line
    aoi.geometry.boundary.plot(
        color=None, edgecolor='k', linewidth=2, ax=ax)

    # add scale
    mlen = 100*METERS_IN_FT
    scalebar = AnchoredSizeBar(ax.transData,
                               mlen, '100 ft', 'lower left',
                               pad=0.1,
                               color='black',
                               frameon=False,
                               size_vertical=1)
    ax.add_artist(scalebar)
    figfile = f'{figdir}/contour.pdf'
    plt.savefig(figfile)
    plt.close()
    return figfile


def plot_hill(hillshade_file, aoi, figdir):
    # hillshade figure
    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches((12, 12))
    fig.set_dpi(300)
    with rasterio.open(hillshade_file, 'r') as src:
        rasterio.plot.show(src, ax=ax, cmap='gray', interpolation='none')
    aoi.geometry.boundary.plot(
        color=None, edgecolor='w', linewidth=2, ax=ax)
    ax.set_title('Hillshade')
    plt.xlabel('East')
    plt.ylabel('North')
    figfile = f'{figdir}/hillshade.png'
    plt.savefig(figfile)
    plt.close()
    return figfile


def plot_slope(slope_file, aoi, figdir):
    # slope figure
    with rasterio.open(slope_file, 'r') as src:
        data = src.read(1)
        fig, ax = plt.subplots(1, 1)
        image_hidden = ax.imshow(data, cmap='gray', vmin=0, vmax=30)
        fig, ax = plt.subplots(1, 1)
        fig.set_size_inches((12, 12))
        fig.set_dpi(300)
        rasterio.plot.show(src, ax=ax, cmap='gray',
                           interpolation='none', vmin=0, vmax=30)
        fig.colorbar(image_hidden, ax=ax)
        ax.set_title('Slope [degrees]')
        plt.xlabel('East')
        plt.ylabel('North')
    aoi.geometry.boundary.plot(
        color=None, edgecolor='r', linewidth=2, ax=ax)
    figfile = f'{figdir}/slope.png'
    plt.savefig(figfile)
    plt.close()
    return figfile


def plot_ba(ba_file, aoi, figdir):
    # ba figure
    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches((12, 12))
    fig.set_dpi(300)
    with rasterio.open(ba_file, 'r') as src:
        fig, ax = plt.subplots(1, 1)
        image_hidden = ax.imshow(src.read(1), cmap='gray')
        fig, ax = plt.subplots(1, 1)
        fig.set_size_inches((12, 12))
        fig.set_dpi(300)
        rasterio.plot.show(src, ax=ax, cmap='gray',
                           interpolation='none')
        fig.colorbar(image_hidden, ax=ax)
        plt.xlabel('East')
        plt.ylabel('North')
    aoi.geometry.boundary.plot(
        color=None, edgecolor='r', linewidth=2, ax=ax)
    figfile = f'{figdir}/ba.png'
    plt.savefig(figfile)
    plt.close()
    return figfile


def plot_naip(naip_file, figdir):
    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches((12, 12))
    fig.set_dpi(300)
    with rasterio.open(naip_file, 'r') as src:
        extent = rasterio.plot.plotting_extent(src)
        arr = src.read()[0:3]
        arr = rasterio.plot.reshape_as_image(arr)
        arr[arr == 0] = 255
        plt.imshow(arr, extent=extent)
        plt.xlabel('East')
        plt.ylabel('North')
    figfile = f'{figdir}/naip.png'
    plt.savefig(figfile)
    plt.close()
    return figfile


def plot_regen(slope_file, ba_file, naip_file, aoi, figdir):
    poly = [aoi.iloc[0].geometry]
    with rasterio.open(slope_file, 'r') as src:
        slope, trans_slope = rasterio.mask.mask(
            src, poly, nodata=np.NaN, crop=True)
        res = src.res
        meta = src.meta
        """
        xx = rasterio.transform.xy(trans_slope,
                                   np.arange(0, meta['width']),
                                   np.zeros(meta['width']))[1]
        yy = rasterio.transform.xy(trans_slope,
                                   np.zeros(meta['height']),
                                   np.arange(0, meta['height']),
                                   )[0]
        """
    with rasterio.open(ba_file, 'r') as src:
        ba, trans_ba = rasterio.mask.mask(
            src, poly, nodata=np.NaN, crop=True)

    # demand same dimensions
    xa = int(np.min((slope.shape[1], ba.shape[1])))
    ya = int(np.min((slope.shape[2], ba.shape[2])))
    slope = slope[0, 0:xa, 0:ya]
    ba = ba[0, 0:xa, 0:ya]

    # categories of slope
    slope30 = slope > 30
    slope15 = (slope > 15) & (slope < 30)
    slope0 = slope < 15
    ba75 = ba > 75
    ba50 = (ba > 50) & (ba < 75)
    ba25 = (ba > 25) & (ba < 50)
    ba0 = ba < 25

    # categories of slope*ba
    pixel_acres = res[0]*res[1]*(1/M2_IN_ACRE)
    total_acres = slope.shape[0]*slope.shape[1]*pixel_acres

    colorarr = np.zeros(slope.shape+(3,)).astype(np.uint8)
    colorarr[~np.isfinite(slope), :] = [255, 255, 255]
    cell_text = []
    cell_colors = np.zeros((3, 4, 3))
    slopes = [slope30, slope15, slope0]
    bas = [ba0, ba25, ba50, ba75]
    cms = [plt.get_cmap('Purples'),
           plt.get_cmap('Blues'),
           plt.get_cmap('Greens'),
           plt.get_cmap('Oranges'),
           ]
    for ii, ss in enumerate(slopes):
        ss = ss*pixel_acres
        cc = []
        for jj, (bb, cm) in enumerate(zip(bas, cms)):
            val = int(np.max((200*(ii+1)/3, 50)))
            color = np.array(cm(val)[0:3])
            cell_colors[ii, jj, :] = color
            colorarr[(ss*bb).astype('bool'), :] = (color*255).astype(np.uint8)
            cc.append(np.round(np.sum(ss*bb), 2))
        cell_text.append(cc)

    # plot map
    fig = plt.figure(figsize=(14, 16), dpi=300)
    gs = GridSpec(4, 2, figure=fig)

    ax1 = fig.add_subplot(gs[0: 2, 0])
    with rasterio.open(naip_file) as src:
        extent = rasterio.plot.plotting_extent(src)
        arr = src.read()[0:3]
        arr = rasterio.plot.reshape_as_image(arr)
        arr[arr == 0] = 255
        ax1.imshow(arr, extent=extent)

    ax2 = fig.add_subplot(gs[0: 2, 1])
    ax2.imshow(colorarr, extent=extent)
    ax2.set_xlabel('East')
    ax2.set_ylabel('North')

    # histograms
    ax2 = fig.add_subplot(gs[2, 0])
    vect = slope.flatten()
    vect = vect[np.isfinite(vect)]
    maxs = np.max(vect)
    step = 5
    aa, bb = np.histogram(vect, bins=np.arange(-5, maxs, step))
    ax2.bar(bb[: -1], aa*pixel_acres, width=step-1)
    ax2.set_xlabel('slope [degrees]')
    ax2.set_ylabel('acres')

    ax3 = fig.add_subplot(gs[2, 1])
    vect = ba.flatten()
    vect = vect[np.isfinite(vect)]
    maxs = np.max(vect)
    mins = np.min(vect)
    step = 5
    aa, bb = np.histogram(vect, bins=np.arange(mins, maxs, step))
    ax3.bar(bb[: -1], aa*pixel_acres, width=step-1)
    ax3.set_xlabel('Basal area (BA) loss [%]')
    ax3.set_ylabel('acres')

    ax4 = fig.add_subplot(gs[3, :])
    columns = ['BA loss < 25%', '25% < BA loss < 50%',
               '50% < BA loss < 75%', 'BA loss > 75%']
    rows = ['Slope > 30%', '30% > Slope > 15%', 'Slope < 15%']

    ax4.axis('off')
    ax4.table(cellText=cell_text,
              rowLabels=rows,
              cellColours=cell_colors,
              colLabels=columns,
              loc='center',
              fontsize=18,
              )
    figfile = f'{figdir}/ba_slope_hist.png'
    plt.savefig(figfile)
    plt.close()
    return figfile, cell_text
