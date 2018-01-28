"""app.sentinel: handle request for Sentinel-tiler"""

import re
import json
from functools import reduce

import numpy as np
import numexpr as ne

from rio_tiler import sentinel2
from rio_tiler.utils import array_to_img, linear_rescale, get_colormap

from aws_sat_api.search import sentinel2 as sentinel_search

from lambda_proxy.proxy import API

SENTINEL_APP = API(app_name="sentinel-tiler")

RATIOS = {
    'ndvi': {
        'eq': '(b08 - b04) / (b08 + b04)',
        'rg': [-1, 1]},
    'ndsi': {
        'eq': '(b02 - b08) / (b02 + b08)',
        'rg': [-1, 1]}}


class SentinelTilerError(Exception):
    """Base exception class"""


@SENTINEL_APP.route('/sentinel/search', methods=['GET'], cors=True)
def search():
    """
    Handle search requests
    """

    query_args = SENTINEL_APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    utm = query_args['utm']
    lat = query_args['lat']
    grid = query_args['grid']
    level = query_args.get('level', 'l1c')
    full = query_args.get('full', True)

    data = list(sentinel_search(utm, lat, grid, full, level))
    info = {
        'request': {'utm': utm, 'lat': lat, 'grid': grid, 'full': full, 'level': level},
        'meta': {'found': len(data)},
        'results': data}

    return ('OK', 'application/json', json.dumps(info))


@SENTINEL_APP.route('/sentinel/bounds/<scene>', methods=['GET'], cors=True)
def sentinel_bounds(scene):
    """
    Handle bounds requests
    """
    info = sentinel2.bounds(scene)
    return ('OK', 'application/json', json.dumps(info))


@SENTINEL_APP.route('/sentinel/metadata/<scene>', methods=['GET'], cors=True)
def sentinel_metadata(scene):
    """
    Handle metadata requests
    """
    query_args = SENTINEL_APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    pmin = query_args.get('pmin', 2)
    pmin = float(pmin) if isinstance(pmin, str) else pmin

    pmax = query_args.get('pmax', 98)
    pmax = float(pmax) if isinstance(pmax, str) else pmax

    info = sentinel2.metadata(scene, pmin, pmax)
    return ('OK', 'application/json', json.dumps(info))


@SENTINEL_APP.route('/sentinel/tiles/<scene>/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'], cors=True)
def sentinel_tile(scene, tile_z, tile_x, tile_y, tileformat):
    """
    Handle tile requests
    """
    query_args = SENTINEL_APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    bands = query_args.get('rgb', '4,3,2')
    bands = tuple(re.findall(r'[0-9A]{2}', bands))

    histoCut = query_args.get('histo', ';'.join(['0,16000'] * len(bands)))
    histoCut = re.findall(r'\d+,\d+', histoCut)
    histoCut = list(map(lambda x: list(map(int, x.split(','))), histoCut))

    if len(bands) != len(histoCut):
        raise SentinelTilerError('The number of bands doesn\'t match the number of histogramm values')

    tilesize = query_args.get('tile', 256)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    tile = sentinel2.tile(scene, tile_x, tile_y, tile_z, bands, tilesize=tilesize)
    rtile = np.zeros((len(bands), tilesize, tilesize), dtype=np.uint8)
    for bdx in range(len(bands)):
        rtile[bdx] = np.where(
            tile[bdx] > 0,
            linear_rescale(tile[bdx], in_range=histoCut[bdx], out_range=[1, 255]), 0)

    tile = array_to_img(rtile, tileformat)
    if tileformat == 'jpg':
        tileformat = 'jpeg'

    return ('OK', f'image/{tileformat}', tile)


@SENTINEL_APP.route('/sentinel/processing/<scene>/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'], cors=True)
def sentinel_ratio(scene, tile_z, tile_x, tile_y, tileformat):
    """
    Handle processing requests
    """
    query_args = SENTINEL_APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    ratio_value = query_args.get('ratio', 'ndvi')

    if ratio_value not in RATIOS.keys():
        raise SentinelTilerError('Invalid ratio: {}'.format(ratio_value))

    equation = RATIOS[ratio_value]['eq']
    band_names = list(set(re.findall('b[0-9]{1,2}', equation)))
    bands = tuple(map(lambda x: x.strip('b'), band_names))

    tilesize = query_args.get('tile', 256)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    tile = sentinel2.tile(scene, tile_x, tile_y, tile_z, bands, tilesize=tilesize)
    for bdx, b in enumerate(band_names):
        globals()[b] = tile[bdx]

    tile = np.where(
        reduce(lambda x, y: x*y, [globals()[i] for i in band_names]) > 0,
        np.nan_to_num(ne.evaluate(equation)),
        -9999)

    range_val = equation = RATIOS[ratio_value]['rg']
    rtile = np.where(
            tile != -9999,
            linear_rescale(tile, in_range=range_val, out_range=[1, 255]), 0).astype(np.uint8)

    tile = array_to_img(rtile, tileformat, color_map=get_colormap(name='cfastie'))
    if tileformat == 'jpg':
        tileformat = 'jpeg'

    return ('OK', f'image/{tileformat}', tile)


@SENTINEL_APP.route('/favicon.ico', methods=['GET'], cors=True)
def favicon():
    """
    favicon
    """
    return('NOK', 'text/plain', '')
