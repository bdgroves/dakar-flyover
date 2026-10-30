"""The Dakar 2027 route: the stage towns ASO published on 30 October 2026, and
the lines drawn between them.

The rally left Saudi Arabia (announced 25 October 2026) and now runs from the
Algarve in Portugal across Morocco to Marrakech, 9-23 January 2027. ASO
publishes each stage's start and finish town and its distances, not the tracks,
so each stage is drawn straight from town to town: special and liaisons share
one line. Stages that start and finish in the same town are loops, marked with a
ring round the town. The transfer (ferry to Nador and the road to Bouarfa) is
dashed. The ferry port and the refuge bivouac weren't named; those two points are
read off ASO's route map and are only approximate (APPROX).

Sources: the FIA's announcement (30 Oct 2026),
https://www.fia.com/news/dakar-return-africa-2027-portugal-and-morocco-set-host-49th-edition
and the stage table as reported by Atalayar and MFE-Live the same day.
The same route is drawn on https://brooksgroves.com/dakar-2027.html (from dakar.json).
"""
from __future__ import annotations

# name: (lat, lon, label shown in the film)
TOWNS = {
    "Algarve": (37.07, -7.97, "Loulé / Faro"),
    "Strait": (36.13, -5.45, "Strait of Gibraltar"),
    "Bouarfa": (32.53, -1.95, "Bouârfa"),
    "Zagora": (30.33, -5.84, "Zagora"),
    "Agadir": (30.42, -9.60, "Agadir"),
    "Smara": (26.74, -11.67, "Smara"),
    "Refuge": (25.90, -14.30, "Refuge bivouac"),
    "Marrakech": (31.63, -8.01, "Marrakech"),
}
APPROX = {"Strait", "Refuge"}

# Each stage, in order: (number, from, to, kind). "stage" is drawn solid, "transfer"
# dashed, and a "loop" (same town both ends) as a ring round its town.
STAGES = [
    ("P", "Algarve", "Algarve", "loop"),
    ("1", "Algarve", "Strait", "stage"),
    ("T", "Strait", "Bouarfa", "transfer"),
    ("2", "Bouarfa", "Bouarfa", "loop"),
    ("3", "Bouarfa", "Bouarfa", "loop"),
    ("4", "Bouarfa", "Zagora", "stage"),
    ("5", "Zagora", "Zagora", "loop"),
    ("6", "Zagora", "Agadir", "stage"),          # rest day in Agadir after this
    ("7", "Agadir", "Smara", "stage"),
    ("8", "Smara", "Refuge", "stage"),           # marathon: no assistance at the refuge
    ("9", "Refuge", "Smara", "stage"),
    ("10", "Smara", "Smara", "loop"),
    ("11", "Smara", "Marrakech", "stage"),
    ("12", "Marrakech", "Marrakech", "loop"),
]

# The lines to draw: every pair of towns joined by a stage or the transfer, once.
LEGS = []
for _n, _a, _b, _kind in STAGES:
    if _a != _b and not any({_a, _b} == {a, b} for a, b, _ in LEGS):
        LEGS.append((_a, _b, "main" if _kind == "stage" else "transfer"))
LOOP_TOWNS = sorted({a for _n, a, b, kind in STAGES if kind == "loop"})
LOOP_KM = 35.0                   # radius of the ring that marks a loop stage

ROUTE_RGB = (242, 179, 94)       # dune gold, as on the website's map
LOOP_RGB = (253, 250, 244)
HALO_RGB = (28, 26, 22)
