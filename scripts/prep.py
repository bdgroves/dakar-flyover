"""Step 2: prepare the terrain and imagery for rendering.

  arabia_dem_300m_x3.tif  the terrain with heights stretched EXAGGERATION times, so
                          the escarpments and plateaus read from the air
  sentinel2_*_graded.png  the imagery toned from surface reflectance (bright sand
                          kept below white, dark lava fields lifted), the open Red
                          Sea painted as one smooth gradient (Sentinel-2's sea is a
                          patchwork of dates), and the route outline and bivouac
                          towns drawn on the ground

    pixi run prep
"""
from __future__ import annotations

import sys

import numpy as np
import rasterio
from PIL import Image, ImageDraw
from rasterio.warp import transform
from scipy import ndimage

import config
import route

# Tone: reflectance WHITE maps to white, with a gamma that lifts the dark basalt
# fields. Desert sand is around 0.3-0.45 reflectance, so this keeps it off white.
WHITE = 0.62
GAMMA = 1.7
SATURATION = 1.05
SEA_KM = (3.0, 9.0)            # real imagery near the coast (reefs, shallows), painted beyond
SEA_SHALLOW = np.array([0.16, 0.36, 0.42], dtype=np.float32)
SEA_DEEP = np.array([0.05, 0.13, 0.25], dtype=np.float32)
LINE_M, HALO_M, DOT_M = 650.0, 1300.0, 1500.0      # route line, its dark edge, town dot radius


def stretch() -> np.ndarray:
    with rasterio.open(config.DEM) as src:
        z = src.read(1).astype(np.float32)
        prof = src.profile
    if not config.DEM_X.exists():
        tmp = config.DEM_X.with_suffix(".part.tif")
        with rasterio.open(tmp, "w", **prof) as dst:
            dst.write(z * config.EXAGGERATION, 1)
        tmp.replace(config.DEM_X)
        print(f"wrote {config.DEM_X.name} (heights x{config.EXAGGERATION:g})")
    return z


def to_image(grid: np.ndarray, left: float, top: float, h: int, w: int, order: int = 1) -> np.ndarray:
    """Sample a DEM-grid array at every image pixel."""
    gl, gt, _, _ = config.grid()
    res = config.IMAGE_RES
    rows = (gt - (top - (np.arange(h) + 0.5) * res)) / config.DEM_RES - 0.5
    cols = (left + (np.arange(w) + 0.5) * res - gl) / config.DEM_RES - 0.5
    out = np.empty((h, w), dtype=np.float32)
    for r0 in range(0, h, 512):
        RR, CC = np.meshgrid(rows[r0:r0 + 512], cols, indexing="ij")
        out[r0:r0 + 512] = ndimage.map_coordinates(grid.astype(np.float32), [RR, CC], order=order, mode="nearest")
    return out


def sea(rgb: np.ndarray, left: float, top: float, z: np.ndarray, coast_km: np.ndarray) -> np.ndarray:
    """Open water: Sentinel-2's own view near the coast, a painted gradient offshore
    (shallow to deep), blended between SEA_KM. Land with no clear pass at all
    borrows its neighbours."""
    h, w = rgb.shape[:2]
    empty = rgb.max(axis=-1) < 1e-3
    water = to_image((z <= 0.5).astype(np.float32), left, top, h, w) > 0.5
    km = to_image(coast_km, left, top, h, w)       # measured on the whole grid, so strips agree
    t = np.clip(km / 60.0, 0, 1)[..., None]
    paint = SEA_SHALLOW * (1 - t) + SEA_DEEP * t
    a = np.clip((km - SEA_KM[0]) / (SEA_KM[1] - SEA_KM[0]), 0, 1)
    a = np.where(empty & water, 1.0, a * water)[..., None]
    rest = empty & ~water
    if rest.any():
        idx = ndimage.distance_transform_edt(rest, return_distances=False, return_indices=True)
        rgb = rgb[idx[0], idx[1]]
    return rgb * (1 - a) + paint * a


def tone(path) -> np.ndarray:
    """Reflectance (x10000) to display colour, 0-1."""
    with rasterio.open(path) as src:
        refl = np.moveaxis(src.read().astype(np.float32), 0, -1) / 10000.0
    empty = refl.max(axis=-1) <= 0.0001
    rgb = np.clip(refl / WHITE, 0, 1) ** (1 / GAMMA)
    rgb[empty] = 0
    return rgb


def draw_route(img: Image.Image, left: float, top: float) -> Image.Image:
    """The route outline and the towns, drawn on the ground."""
    res = config.IMAGE_RES
    names = list(route.TOWNS)
    xs, ys = transform("EPSG:4326", config.CRS, [route.TOWNS[n][1] for n in names],
                       [route.TOWNS[n][0] for n in names])
    px = {n: ((x - left) / res, (top - y) / res) for n, x, y in zip(names, xs, ys)}
    d = ImageDraw.Draw(img)
    lw, hw, r = (max(1, round(m / res)) for m in (LINE_M, HALO_M, DOT_M))
    hw = max(hw, lw + 2)
    for a, b, kind in route.LEGS:
        d.line([px[a], px[b]], fill=route.HALO_RGB, width=hw)
    for a, b, kind in route.LEGS:
        if kind == "main":
            d.line([px[a], px[b]], fill=route.ROUTE_RGB, width=lw)
        else:                                           # dotted: the loops out of Bisha
            (x0, y0), (x1, y1) = px[a], px[b]
            n = max(2, int(np.hypot(x1 - x0, y1 - y0) / (lw * 4)))
            for k in range(0, n, 2):
                u0, u1 = k / n, min((k + 1) / n, 1)
                d.line([(x0 + (x1 - x0) * u0, y0 + (y1 - y0) * u0), (x0 + (x1 - x0) * u1, y0 + (y1 - y0) * u1)],
                       fill=route.LOOP_RGB, width=lw)
    for n in names:
        x, y = px[n]
        d.ellipse([x - r - 2, y - r - 2, x + r + 2, y + r + 2], fill=route.HALO_RGB)
        d.ellipse([x - r, y - r, x + r, y + r], fill=route.LOOP_RGB if n == "Dawasir" else route.ROUTE_RGB)
    return img


def grade(path, left, top, z, coast_km) -> None:
    Image.MAX_IMAGE_PIXELS = None
    rgb = sea(tone(path), left, top, z, coast_km)
    lum = (rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32))[..., None]
    rgb = np.clip(lum + (rgb - lum) * SATURATION, 0.0, 1.0)
    rgb = np.where(rgb > 0.7, 0.7 + (rgb - 0.7) * 0.75, rgb)       # ease the brightest sand
    rgb += 0.10 * (rgb - 0.5) * (1.0 - np.abs(2.0 * rgb - 1.0))     # gentle S-curve
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8))
    draw_route(img, left, top).save(config.graded(path))
    print(f"wrote {config.graded(path).name}")


def main() -> int:
    tiles = config.image_tiles()
    missing = [p.name for p in [config.DEM] + [t[0] for t in tiles] if not p.exists()]
    if missing:
        print("Missing", ", ".join(missing), "- run: pixi run data")
        return 1
    z = stretch()
    coast_km = ndimage.distance_transform_edt(z <= 0.5) * config.DEM_RES / 1000.0   # kilometres offshore
    for path, left, top, _, _ in tiles:
        grade(path, left, top, z, coast_km)
    return 0


if __name__ == "__main__":
    sys.exit(main())
