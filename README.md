# Dakar 2027 flyover

A flight around the Dakar Rally 2027 loop in Saudi Arabia on a January afternoon, rendered with [forge3d](https://github.com/milos-agathon/forge3d):

1. It opens high over the Red Sea, with the whole loop laid out to the east.
2. It drops to the start at King Abdullah Economic City and runs north up the coast past Yanbu.
3. It turns inland to AlUla, then east along the southern edge of the Nafud to Ha'il.
4. It crosses the central plateau to Al Duwadimi and follows the first marathon south.
5. It reaches Bisha for the rest day, with a look east along the loops to Wadi Ad-Dawasir.
6. It goes west to Al Bahah and over the edge of the Asir escarpment.
7. It finishes with the long transfer back to the Red Sea and King Abdullah Economic City.

The route on the ground is the **outline ASO announced in May 2026**: the bivouac towns in order, joined by straight lines. It's a sketch of the order, not the racing line. The stage-by-stage route comes out in December, and then this gets re-rendered. The same outline is mapped on [brooksgroves.com/dakar-2027.html](https://brooksgroves.com/dakar-2027.html).

## Run it

```powershell
pixi install
pixi run data       # Copernicus DEM tiles + Sentinel-2 imagery, both on AWS; restartable
pixi run prep
pixi run path       # the flight drawn on a map -> out\flight_map.png
pixi run stills     # eight full-size frames along the way -> out\stills\
pixi run render     # the whole flight, 1920x1080 at 30 fps -> out\dakar_2027_flyover.mp4
```

`pixi run preview` makes a quick, small version first. To change the flight, edit `KEYS` in `scripts/flight.py`; to change the route, edit `scripts/route.py`.

## How it's made

- **Terrain:** Copernicus GLO-90 DEM on a 300 m grid in a transverse Mercator centred on 41.5°E. The open Red Sea has no DEM tiles, so it's sea level.
- **Heights are stretched three times** (`EXAGGERATION` in `scripts/config.py`). The land is over a thousand kilometres across and at most about three kilometres high, so at true scale it reads as flat from the air. The film says so.
- **Imagery:** Sentinel-2 true colour at 150 m, read from each scene's overviews, so only a few megabytes per scene come down. It uses the clearest passes of December 2025 and January 2026 (the season the rally runs in), first keeping only ground the scene classification calls clear, then filling the rest from the clearest pass available. Bright sand is sometimes classed as cloud, and the second pass catches it.
- **On the ground:** the route in dune gold with a dark edge, the loops out of Bisha dotted white, and a dot at each bivouac town.
- **On screen:** the town names, placed by projecting each town through the same camera as the viewer. A dusty haze thickens with distance from the camera, so far ground fades into the horizon.
- **Sun:** placed for January 10, 2027 at 4:30 pm Arabia time, low in the south-west.

### One forge3d detail worth knowing

The viewer's orbit camera caps its radius (eye to target) at about 5% of the terrain's width, without saying so. Above that, a high camera is quietly pulled down toward its target. `flight.camera()` keeps the same eye and view direction but moves the target along the line of sight to within 40 km, so the view is the one asked for. This was checked by draping a grid of markers and comparing where they render with where `flight.project()` puts them: they agree to within a few pixels.

## Data

- **Terrain:** Copernicus GLO-90 DEM (ESA / Copernicus Programme, via the AWS open-data bucket).
- **Imagery:** Sentinel-2 Level-2A (ESA Copernicus), via Element 84's Earth Search.
- **Route outline:** ASO's May 2026 announcement, as reported by [ADV Pulse](https://www.advpulse.com/adv-news/dakar-2027-route-announced-longest-distance-of-the-saudi-era/).
