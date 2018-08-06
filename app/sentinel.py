"""Handle request for Sentinel-tiler."""

import re
import json

import numpy as np

from rio_tiler import sentinel2
from rio_tiler.utils import (
    array_to_img, linear_rescale, get_colormap, expression, b64_encode_img
)
from aws_sat_api.search import sentinel2 as sentinel_search

from lambda_proxy.proxy import API

APP = API(app_name="sentinel-tiler")


class SentinelTilerError(Exception):
    """Base exception class."""


@APP.route("/sentinel/search", methods=["GET"], cors=True)
def search():
    """Handle search requests."""
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    utm = query_args["utm"]
    lat = query_args["lat"]
    grid = query_args["grid"]
    level = query_args.get("level", "l1c")
    full = query_args.get("full", True)

    data = list(sentinel_search(utm, lat, grid, full, level))
    info = {
        "request": {"utm": utm, "lat": lat, "grid": grid, "full": full, "level": level},
        "meta": {"found": len(data)},
        "results": data,
    }

    return ("OK", "application/json", json.dumps(info))


@APP.route("/sentinel/bounds/<scene>", methods=["GET"], cors=True)
def bounds(scene):
    """Handle bounds requests."""
    info = sentinel2.bounds(scene)
    return ("OK", "application/json", json.dumps(info))


@APP.route("/sentinel/metadata/<scene>", methods=["GET"], cors=True)
def metadata(scene):
    """Handle metadata requests."""
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    pmin = query_args.get("pmin", 2)
    pmin = float(pmin) if isinstance(pmin, str) else pmin

    pmax = query_args.get("pmax", 98)
    pmax = float(pmax) if isinstance(pmax, str) else pmax

    info = sentinel2.metadata(scene, pmin, pmax)
    return ("OK", "application/json", json.dumps(info))


@APP.route(
    "/sentinel/tiles/<scene>/<int:z>/<int:x>/<int:y>.<ext>", methods=["GET"], cors=True
)
def tile(scene, tile_z, tile_x, tile_y, tileformat):
    """Handle tile requests."""
    if tileformat == "jpg":
        tileformat = "jpeg"

    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    bands = query_args.get("rgb", "04,03,02")
    bands = tuple(re.findall(r"[0-9A]{2}", bands))

    histoCut = query_args.get("histo", "-".join(["0,16000"] * len(bands)))
    histoCut = re.findall(r"\d+,\d+", histoCut)
    histoCut = list(map(lambda x: list(map(int, x.split(","))), histoCut))

    if len(bands) != len(histoCut):
        raise SentinelTilerError(
            "The number of bands doesn't match the number of histogramm values"
        )

    tilesize = query_args.get("tile", 256)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    tile, mask = sentinel2.tile(scene, tile_x, tile_y, tile_z, bands, tilesize=tilesize)

    rtile = np.zeros((len(bands), tilesize, tilesize), dtype=np.uint8)
    for bdx in range(len(bands)):
        rtile[bdx] = np.where(
            mask,
            linear_rescale(tile[bdx], in_range=histoCut[bdx], out_range=[0, 255]),
            0,
        )
    img = array_to_img(rtile, mask=mask)
    str_img = b64_encode_img(img, tileformat)
    return ("OK", f"image/{tileformat}", str_img)


@APP.route(
    "/sentinel/processing/<scene>/<int:z>/<int:x>/<int:y>.<ext>",
    methods=["GET"],
    cors=True,
)
def ratio(scene, tile_z, tile_x, tile_y, tileformat):
    """Handle processing requests."""
    if tileformat == "jpg":
        tileformat = "jpeg"

    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    ratio_value = query_args["ratio"]
    range_value = query_args.get("range", [-1, 1])

    tilesize = query_args.get("tile", 256)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    tile, mask = expression(
        scene, tile_x, tile_y, tile_z, ratio_value, tilesize=tilesize
    )
    if len(tile.shape) == 2:
        tile = np.expand_dims(tile, axis=0)

    rtile = np.where(
        mask, linear_rescale(tile, in_range=range_value, out_range=[0, 255]), 0
    ).astype(
        np.uint8
    )
    img = array_to_img(rtile, color_map=get_colormap(name="cfastie"), mask=mask)
    str_img = b64_encode_img(img, tileformat)
    return ("OK", f"image/{tileformat}", str_img)


@APP.route("/favicon.ico", methods=["GET"], cors=True)
def favicon():
    """Favicon."""
    return ("NOK", "text/plain", "")
