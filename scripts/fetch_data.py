"""Step 1: download the terrain and imagery for the Dakar 2027 flyover into data/.

  arabia_dem_300m.tif   Copernicus GLO-90 elevation (ESA, free), the 1-degree tiles
                        from the Red Sea to beyond Wadi Ad-Dawasir, on a 300 m grid.
                        Open sea has no tiles; it is set to sea level.
  sentinel2_*.png       Sentinel-2 true colour at 150 m, read from each scene's
                        overviews (so only a few MB per scene come down), from the
                        clearest passes of December 2025 and January 2026, the
                        season the rally runs in

Both come from public AWS buckets (no account needed); files that already exist are
skipped, so an interrupted run can simply be restarted.

    pixi run data
"""
from __future__ import annotations

import json
import math
import sys
import time
import urllib.request
from urllib.parse import parse_qs, urlparse

import numpy as np
import rasterio
from PIL import Image
from rasterio.errors import RasterioIOError
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_geom
from scipy import ndimage

import config

COP = "https://copernicus-dem-90m.s3.amazonaws.com"
STAC = "https://earth-search.aws.element84.com/v1/search"
# Sentinel-2 scene classes to keep: vegetation, bare, water, unclassified
# (dropping no-data, saturated, dark/cloud shadow, cloud, cirrus and snow).
# Bright desert is sometimes called cloud; a second, looser pass fills those.
GOOD_SCL = {2, 4, 5, 6, 7}
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", VSI_CACHE="TRUE",
                GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2")


def cop_url(lat: int, lon: int) -> str:
    ns = f"N{lat:02d}" if lat >= 0 else f"S{-lat:02d}"
    ew = f"E{lon:03d}" if lon >= 0 else f"W{-lon:03d}"
    name = f"Copernicus_DSM_COG_30_{ns}_00_{ew}_00_DEM"
    return f"{COP}/{name}/{name}.tif"


def build_dem() -> None:
    if config.DEM.exists():
        print(f"Terrain already present: {config.DEM.name}")
        return
    left, top, w, h = config.grid()
    tf = from_origin(left, top, config.DEM_RES, config.DEM_RES)
    dem = np.full((h, w), np.nan, dtype=np.float32)
    tiles = [(la, lo) for la in range(math.floor(config.SOUTH), math.floor(config.NORTH) + 1)
             for lo in range(math.floor(config.WEST), math.floor(config.EAST) + 1)]
    print(f"Copernicus DEM: {len(tiles)} tiles -> {w} x {h} at {config.DEM_RES:g} m")
    sea = 0
    with rasterio.Env(**GDAL_ENV):
        for la, lo in tiles:
            url = cop_url(la, lo)
            part = np.full_like(dem, np.nan)
            try:
                src = rasterio.open("/vsicurl/" + url)
            except RasterioIOError:
                sea += 1                                   # all-sea tiles don't exist
                continue
            with src:
                print(f"  {url.rsplit('/', 1)[-1]}")
                reproject(rasterio.band(src, 1), part, dst_transform=tf, dst_crs=config.CRS,
                          src_nodata=src.nodata, dst_nodata=np.nan, resampling=Resampling.average)
            fill = np.isnan(dem) & np.isfinite(part)
            dem[fill] = part[fill]
    print(f"  {sea} tiles are open sea")
    dem[np.isnan(dem)] = 0.0
    dem = np.maximum(dem, 0.0)                             # sea level, not the sea floor
    prof = {"driver": "GTiff", "width": w, "height": h, "count": 1, "dtype": "float32", "crs": config.CRS,
            "transform": tf, "nodata": None, "compress": "deflate", "tiled": True}
    tmp = config.DEM.with_suffix(".part.tif")
    with rasterio.open(tmp, "w", **prof) as dst:
        dst.write(dem, 1)
    tmp.replace(config.DEM)
    print(f"Saved {config.DEM.name}: {dem.min():,.0f}-{dem.max():,.0f} m")


def post(body: dict) -> dict:
    req = urllib.request.Request(STAC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    for k in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:                       # noqa: BLE001
            print(f"  search attempt {k + 1}: {e}")
            time.sleep(4 * (k + 1))
    raise RuntimeError("Sentinel-2 search failed")


def stac_search(dates) -> list[dict]:
    """Every scene in the window under MAX_CLOUD, following the search's pages."""
    body = {"collections": ["sentinel-2-l2a"], "bbox": [config.WEST, config.SOUTH, config.EAST, config.NORTH],
            "datetime": f"{dates[0]}T00:00:00Z/{dates[1]}T23:59:59Z", "limit": 250,
            "query": {"eo:cloud_cover": {"lt": config.MAX_CLOUD}}}
    feats = []
    for _ in range(40):
        page = post(body)
        feats += page["features"]
        nxt = next((ln for ln in page.get("links", []) if ln.get("rel") == "next"), None)
        if not nxt or not page["features"]:
            break
        if "body" in nxt:
            body = {**body, **nxt["body"]} if nxt.get("merge") else nxt["body"]
        else:                                           # a GET link: carry its page token over
            token = parse_qs(urlparse(nxt["href"]).query).get("next")
            if not token:
                break
            body = {**body, "next": token[0]}
    print(f"  {len(feats)} scenes between {dates[0]} and {dates[1]}")
    return feats


def scenes() -> list[dict]:
    """Passes to use, best first: the main window by cloud cover, then the fallback window."""
    out, seen = [], set()
    for dates in (config.IMAGE_DATE, config.IMAGE_FALLBACK):
        feats = sorted(stac_search(dates), key=lambda f: f["properties"].get("eo:cloud_cover", 100))
        for f in feats:
            if f["id"] not in seen and "visual" in f["assets"] and "scl" in f["assets"]:
                seen.add(f["id"])
                out.append(f)
    return out


def open_overview(href: str, res: float):
    """Open a Sentinel-2 COG at the coarsest overview still finer than `res`."""
    url = "/vsicurl/" + href
    with rasterio.open(url) as src:
        native = abs(src.transform.a)
        factors = src.overviews(1)
    level = None
    for i, f in enumerate(factors):
        if native * f <= res / 1.5:
            level = i
    return rasterio.open(url, overview_level=level) if level is not None else rasterio.open(url)


def build_image(path, left, top, right, bottom, items) -> None:
    if path.exists():
        print(f"Imagery already present: {path.name}")
        return
    res = config.IMAGE_RES
    w, h = round((right - left) / res), round((top - bottom) / res)
    tf = from_origin(left, top, res, res)
    rgb = np.zeros((3, h, w), dtype=np.uint8)
    have = np.zeros((h, w), dtype=bool)
    print(f"{path.name}: {w} x {h} px at {res:g} m")
    with rasterio.Env(**GDAL_ENV):
        # first only clear ground, then anything at all where nothing clear was found
        for strict in (True, False):
            for f in items:
                foot = transform_geom("EPSG:4326", config.CRS, f["geometry"])
                inside = rasterize([(foot, 1)], out_shape=(h, w), transform=tf, dtype=np.uint8).astype(bool)
                todo = inside & ~have
                if todo.sum() < 0.002 * w * h:
                    continue
                if strict:
                    scl = np.zeros((h, w), dtype=np.uint8)
                    with open_overview(f["assets"]["scl"]["href"], res) as src:
                        reproject(rasterio.band(src, 1), scl, dst_transform=tf, dst_crs=config.CRS,
                                  src_nodata=0, dst_nodata=0, resampling=Resampling.nearest)
                    good = np.isin(scl, list(GOOD_SCL)) & todo
                    good = ndimage.binary_erosion(good, iterations=1)       # stay clear of cloud edges
                    if good.sum() < 0.002 * w * h:
                        continue
                else:
                    good = todo
                part = np.zeros((3, h, w), dtype=np.uint8)
                with open_overview(f["assets"]["visual"]["href"], res) as src:
                    for b in range(3):
                        reproject(rasterio.band(src, b + 1), part[b], dst_transform=tf, dst_crs=config.CRS,
                                  src_nodata=0, dst_nodata=0, resampling=Resampling.average)
                good &= part.min(axis=0) > 0
                rgb[:, good] = part[:, good]
                have |= good
                p = f["properties"]
                print(f"  {'' if strict else 'loose '}{p.get('datetime', '')[:10]} {f['id'][:26]:<26} "
                      f"cloud {p.get('eo:cloud_cover', 0):4.1f}%  -> {have.mean():6.1%} filled")
                if have.mean() > 0.9995:
                    break
            if have.mean() > 0.9995:
                break
    if not have.all():
        # open sea far from the coast is outside every Sentinel-2 tile; prep paints it
        print(f"  {1 - have.mean():.2%} has no imagery (open sea): left black for prep")
    tmp = path.with_suffix(".part.png")
    Image.fromarray(np.moveaxis(rgb, 0, -1)).save(tmp)
    tmp.replace(path)
    print(f"Saved {path.name}")


def main() -> int:
    config.DATA.mkdir(parents=True, exist_ok=True)
    build_dem()
    tiles = config.image_tiles()
    if all(p.exists() for p, *_ in tiles):
        print("Imagery already present")
    else:
        items = scenes()
        dates = sorted({f["properties"]["datetime"][:10] for f in items})
        print(f"Sentinel-2: {len(items)} passes to draw from, clearest first ({dates[0]} to {dates[-1]})")
        for t in tiles:
            build_image(*t, items)
    print("Data ready. Next: pixi run prep")
    return 0


if __name__ == "__main__":
    sys.exit(main())
