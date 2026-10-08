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

## Run it on GitHub

The renders run on GitHub Actions, on CPUs with Mesa's software Vulkan, so no GPU or local Python environment is needed:

1. **Data and stills** runs on every push to `scripts/`, or by hand from the Actions tab. It downloads and prepares the data, saves it to the `prep-data` branch, and renders eight test frames. The frames and the flight map land on the [`stills` branch](../../tree/stills), to look at right on GitHub. A push that only changes the flight or the look reuses the data it already downloaded; tick **fresh** to download again.
2. **Render the flyover** is run by hand. It splits the flight across 40 parallel jobs and joins their frames into the video, which comes back as the `flyover` artifact. If some pieces fail, run it again with the failed run's ID as **reuse_run**, and only the missing frames are rendered.

## Run it locally

With a GPU and a pixi environment that your system allows to run:

```powershell
pixi install
pixi run data       # Copernicus DEM tiles + Sentinel-2 imagery, both on AWS; restartable
pixi run prep
pixi run path       # the flight drawn on a map -> out\flight_map.png
pixi run stills     # eight full-size frames along the way -> out\stills\
pixi run render     # the whole flight, 1920x1080 at 30 fps -> out\dakar_2027_flyover.mp4
```

`pixi run preview` makes a quick, small version first. To change the flight, edit `KEYS` in `scripts/flight.py`; to change the route, edit `scripts/route.py`.

### On Windows with Smart App Control

Smart App Control blocks the new, unsigned DLLs and `interactive_viewer.exe` that a fresh `pixi install` brings in, so this repo's own environment won't run. An older forge3d environment that Windows already trusts will, and it uses the GPU directly. Here that's `humphreys-orbit` (forge3d 1.39), reached through an `f3d` function in the PowerShell profile:

```powershell
function f3d {
    $e = "C:\Users\brook\Projects\humphreys-orbit\.pixi\envs\default"
    $env:PATH = "$e\Scripts;$e\Library\bin;$e;" + $env:PATH   # so forge3d finds interactive_viewer.exe
    $env:GDAL_DATA = "$e\Library\share\gdal"
    & "$e\python.exe" @args
}
```

Then skip the download and take the prepared data from the `prep-data` branch:

```powershell
git pull
git archive -o prep.tar origin/prep-data
mkdir data -Force; tar -xf prep.tar -C data; Remove-Item prep.tar
f3d scripts\render.py --stills "2,13,30" --size 960x540 --lite   # quick check
f3d scripts\render.py --preview

# the full flight, as numbered frames: restarts itself after a stall, skipping finished frames
do { f3d scripts\render.py --frames-dir out\frames --lite } until ($LASTEXITCODE -eq 0)
f3d scripts\render.py --encode out\frames                         # -> out\dakar_2027_flyover.mp4
```

Quote the `--stills` list: through `f3d`, PowerShell would otherwise split it into separate values. Don't minimize the viewer window while it renders; a minimized window stops drawing and the render stalls.

Never run `pixi install`, `update` or `add` inside `humphreys-orbit`, and don't delete its `.pixi` folder: new copies of the DLLs would be blocked. If it ever stops working, point `$e` at another old environment (solstice, wa-smoke). WSL2 Ubuntu is the fallback; there Vulkan only sees the CPU, but OpenGL reaches the NVIDIA card with `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA GALLIUM_DRIVER=d3d12`.

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
