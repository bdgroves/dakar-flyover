# Dakar 2027 flyover

A flight along the Dakar Rally 2027 route, from Portugal across Morocco, on a January afternoon, rendered with [forge3d](https://github.com/milos-agathon/forge3d):

1. It opens high over the Atlantic, with the whole route laid out to the south-east.
2. It drops to the start in the Algarve, at Loulé / Faro, and runs east along the coast to the Strait of Gibraltar.
3. It crosses the Mediterranean with the ferry and follows the transfer to Bouârfa.
4. It turns south-west through the Merzouga dunes to Zagora, then west over the Anti-Atlas to Agadir and the rest day.
5. It heads south into the Sahara to Smara, looking out toward the refuge bivouac of the marathon.
6. It finishes with the longest day, north over the High Atlas to Marrakech.

The route on the ground is **the one ASO published on 30 October 2026**, after the Saudi edition was called off. ASO publishes each stage's start and finish town and its distances, not the tracks, so each stage is a straight line from town to town. A ring round a town marks loop stages that start and finish there, and the transfer is dashed. The ferry port and the refuge bivouac weren't named, so those two points (hollow dots) are read off ASO's route map. The same route is mapped on [brooksgroves.com/dakar-2027.html](https://brooksgroves.com/dakar-2027.html), with the full stage table.

The first version of this flyover followed the Saudi route outline from May 2026 (a loop from King Abdullah Economic City). It's in this repo's history up to commit 7f8c870.

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
f3d scripts\render.py --stills "2,11,34" --size 960x540 --lite   # quick check
f3d scripts\render.py --preview

# the full flight, as numbered frames: restarts itself after a stall, skipping finished frames
# (only when the flight or route has changed: Remove-Item out\frames -Recurse, or old frames are reused)
do { f3d scripts\render.py --frames-dir out\frames --lite } until ($LASTEXITCODE -eq 0)
f3d scripts\render.py --encode out\frames                         # -> out\dakar_2027_flyover.mp4
```

Quote the `--stills` list: through `f3d`, PowerShell would otherwise split it into separate values. Don't minimize the viewer window while it renders; a minimized window stops drawing and the render stalls.

Never run `pixi install`, `update` or `add` inside `humphreys-orbit`, and don't delete its `.pixi` folder: new copies of the DLLs would be blocked. If it ever stops working, point `$e` at another old environment (solstice, wa-smoke). WSL2 Ubuntu is the fallback; there Vulkan only sees the CPU, but OpenGL reaches the NVIDIA card with `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA GALLIUM_DRIVER=d3d12`.

## How it's made

- **Terrain:** Copernicus GLO-90 DEM on a 300 m grid in a transverse Mercator centred on 8°W. The open Atlantic and Mediterranean have no DEM tiles, so they're sea level.
- **Heights are stretched three times** (`EXAGGERATION` in `scripts/config.py`). The land is about 1,500 kilometres across and at most about four kilometres high (Toubkal, in the High Atlas), so at true scale it reads as flat from the air. The film says so.
- **Imagery:** Sentinel-2 true colour at 200 m, read from each scene's overviews, so only a few megabytes per scene come down. 200 m keeps each of the five imagery strips under 8,192 pixels wide, the usual GPU texture limit. It uses the clearest passes of December 2025 and January 2026 (the season the rally runs in), first keeping only ground the scene classification calls clear (snow counts as clear: the High Atlas has it in January), then filling the rest from the clearest pass available. Bright sand is sometimes classed as cloud, and the second pass catches it.
- **On the ground:** each stage in dune gold with a dark edge, a gold ring round each town with a loop stage, the transfer dashed, and a dot at each bivouac town (hollow where the place is approximate).
- **On screen:** the town names, placed by projecting each town through the same camera as the viewer. A dusty haze thickens with distance from the camera, so far ground fades into the horizon.
- **Sun:** placed for January 16, 2027 at 5:30 pm Morocco time, about 14 degrees up in the south-west.

### One forge3d detail worth knowing

The viewer's orbit camera caps its radius (eye to target) at about 5% of the terrain's width, without saying so. Above that, a high camera is quietly pulled down toward its target. `flight.camera()` keeps the same eye and view direction but moves the target along the line of sight to within 40 km, so the view is the one asked for. This was checked by draping a grid of markers and comparing where they render with where `flight.project()` puts them: they agree to within a few pixels.

## Data

- **Terrain:** Copernicus GLO-90 DEM (ESA / Copernicus Programme, via the AWS open-data bucket).
- **Imagery:** Sentinel-2 Level-2A (ESA Copernicus), via Element 84's Earth Search.
- **Route:** ASO's announcement of 30 October 2026, as reported by the [FIA](https://www.fia.com/news/dakar-return-africa-2027-portugal-and-morocco-set-host-49th-edition), [Atalayar](https://www.atalayar.com/en/articulo/sports/2027-dakar-rally-official-route-between-portugal-and-morocco-key-dates-and-reasons-for-the-change-of-venue/20261030110854230172.html) and [MFE-Live](https://www.mfe-live.com/2026/10/30/dakar-2027-les-etapes-au-portugal-et-au-maroc-arrivee-a-marrakech/). Stage towns and dates are in `scripts/route.py`.
