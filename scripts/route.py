"""The Dakar 2027 route outline: the bivouac towns in the order ASO announced
them in May 2026, and the lines drawn between them.

The lines are straight, town to town. They are a sketch of the order, not the
racing line: the stage-by-stage route comes out in December, and the exact
tracks only on the day. When it does, replace TOWNS and LEGS and re-render.

Source: ASO's route announcement, as reported by ADV Pulse (May 15, 2026),
https://www.advpulse.com/adv-news/dakar-2027-route-announced-longest-distance-of-the-saudi-era/
The same order is drawn on https://brooksgroves.com/dakar-2027.html.
"""
from __future__ import annotations

# name: (lat, lon, label shown in the film)
TOWNS = {
    "KAEC": (22.40, 39.10, "King Abdullah Economic City"),
    "Yanbu": (24.09, 38.06, "Yanbu"),
    "AlUla": (26.61, 37.92, "AlUla"),
    "Hail": (27.52, 41.69, "Ha'il"),
    "Duwadimi": (24.51, 44.39, "Al Duwadimi"),
    "Bisha": (20.00, 42.60, "Bisha"),
    "Dawasir": (20.47, 44.78, "Wadi Ad-Dawasir"),
    "Bahah": (20.01, 41.47, "Al Bahah"),
}

# The loop, in order. "main" legs are drawn solid; "loop" legs are the specials
# that run out from Bisha to Wadi Ad-Dawasir and back, drawn dotted. The first
# marathon ends at a refuge bivouac somewhere between Al Duwadimi and Bisha; its
# place hasn't been announced, so that leg is drawn straight through.
LEGS = [
    ("KAEC", "Yanbu", "main"),
    ("Yanbu", "AlUla", "main"),
    ("AlUla", "Hail", "main"),
    ("Hail", "Duwadimi", "main"),
    ("Duwadimi", "Bisha", "main"),
    ("Bisha", "Dawasir", "loop"),
    ("Bisha", "Bahah", "main"),
    ("Bahah", "KAEC", "main"),
]

ROUTE_RGB = (242, 179, 94)       # dune gold, as on the website's map
LOOP_RGB = (253, 250, 244)
HALO_RGB = (28, 26, 22)
