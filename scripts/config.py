"""Shared settings for the Dakar 2027 flyover."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"

# A transverse Mercator centred on the loop, in metres. The rally spans about
# 8 degrees of longitude, wider than one UTM zone, so it gets its own meridian.
CRS = "+proj=tmerc +lat_0=0 +lon_0=41.5 +k=1 +x_0=500000 +y_0=0 +datum=WGS84 +units=m +no_defs"

# The whole loop, from the Red Sea to Wadi Ad-Dawasir and from the Asir
# highlands to the southern edge of the Nafud, with a few hundred kilometres
# spare on every side so the camera never sees the edge of the world.
WEST, EAST = 36.3, 47.6
SOUTH, NORTH = 17.4, 29.9
DEM_RES = 300.0                # metres; the source is the 90 m Copernicus DEM
IMAGE_RES = 150.0              # metres; Sentinel-2 is read from its overviews
IMAGE_TILES = 4                # the imagery is split into north-south strips to keep each texture a sensible size

# The land is a thousand kilometres across and at most three high, so heights are
# stretched to be seen from the air. Every flight altitude is in stretched metres.
EXAGGERATION = 3.0

DEM = DATA / "arabia_dem_300m.tif"            # true heights
DEM_X = DATA / "arabia_dem_300m_x3.tif"       # stretched, what the viewer loads
IMAGE_DATE = ("2025-12-01", "2026-01-31")     # the season the rally runs in
IMAGE_FALLBACK = ("2025-10-01", "2026-03-31")  # to fill any cloudy gaps
MAX_CLOUD = 15                                 # percent, per Sentinel-2 tile


def image_path(k: int) -> Path:
    return DATA / f"sentinel2_{k}.tif"   # reflectance x10000, red/green/blue


def graded(path: Path) -> Path:
    return path.with_name(path.stem + "_graded.png")


# Late afternoon in the middle of the rally: January 10, 2027, 4:30 pm Arabia time.
# The sun is low in the south-west, so the escarpments throw long shadows.
SUN_UTC = (2027, 1, 10, 13, 30, 0)
SUN_LATLON = (23.5, 41.5)

VIDEO = OUT / "dakar_2027_flyover.mp4"


def grid():
    """(left, top, width px, height px) of the DEM grid in CRS metres."""
    from rasterio.warp import transform_bounds
    l, b, r, t = transform_bounds("EPSG:4326", CRS, WEST, SOUTH, EAST, NORTH)
    left, top = round(l / 1000) * 1000, round(t / 1000) * 1000
    w, h = int((r - left) // DEM_RES), int((top - b) // DEM_RES)
    return left, top, w, h


def bounds():
    left, top, w, h = grid()
    return left, top, left + w * DEM_RES, top - h * DEM_RES


def image_tiles():
    """(path, left, top, right, bottom) for each imagery strip, north first."""
    left, top, right, bottom = bounds()
    edges = [top - (top - bottom) * k / IMAGE_TILES for k in range(IMAGE_TILES + 1)]
    edges = [round(e / IMAGE_RES) * IMAGE_RES for e in edges]
    edges[0], edges[-1] = top, bottom
    return [(image_path(k), left, edges[k], right, edges[k + 1]) for k in range(IMAGE_TILES)]


def lonlat_bounds():
    """(west, south, east, north) that the projected grid actually covers. A rectangle in
    this projection bulges past WEST/EAST/SOUTH/NORTH at its corners, so downloads use this."""
    from rasterio.warp import transform_bounds
    return transform_bounds(CRS, "EPSG:4326", *(lambda l, t, r, b: (l, b, r, t))(*bounds()), densify_pts=101)


LEFT, TOP, RIGHT, BOTTOM = bounds()
