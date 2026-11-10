#!/usr/bin/env python3
"""Render the fixed six-cube aggregate snapshot using only the standard library.

New cases require an explicit new snapshot; this figure retains the four
inspected development cases and the two source-frozen spatial validations.
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
files = ["centre-path-development-results.json", "centre-path-heldout-results.json"]
cases = ["s5_03997_01497_03997_256", "s1_00497_02497_02997_256",
         "s1_10997_02997_02997_256", "s5_14997_01497_01497_256",
         "s1_08997_02997_02497_256", "s5_07997_02997_05497_256"]
rows = [r for f in files for r in json.loads((ROOT/f).read_text())["matched"]
        if r["stage"] == "clean"]
assert len(rows) == 24 and {r["case"] for r in rows} == set(cases)
lookup = {(r["case"], r["radius_vox"], r["bracket"]): r for r in rows}
assert len(lookup) == 24 and all(r[side]["boundary_switches"] == 0 for r in rows for side in ("dp", "baseline"))
ink, blue, grey, guide = "#172a4b", "#254bdd", "#5b6c83", "#d8e3ef"
parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="904" viewBox="0 0 1080 904" role="img" aria-labelledby="title desc">',
         '<title id="title">Fixed DP: all six native-clean cube comparisons</title>',
         '<desc id="desc">Four development cubes and two new spatial parameter-validation cubes. Radius 2 at matched manual coverage and radius 3 with the same selected prefixes. Markers are lower and upper whole-curve coverage brackets. Full source aggregates are linked in the repository.</desc>',
         '<rect width="1080" height="904" fill="#ffffff"/>',
         '<g font-family="Arial, sans-serif">']

def text(x, y, value, size=14, color=ink, weight=400, anchor="start"):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def line(x1, y1, x2, y2, color=guide, width=1):
    parts.append(f'<line x1="{x1:.3f}" y1="{y1}" x2="{x2:.3f}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')


def axis(value):
    assert -8 <= value <= 8, value
    return 368 + (value + 8) * 31


text(40, 51, "Continuous center paths: the full spatial picture", 29, weight=700)
text(40, 83, "Fixed-model postprocessing with the original cleanup and evaluator.", 16, grey)
text(40, 107, "Four inspected development cubes, then two unscored at the public source freeze.", 15, grey)
line(40, 139, 70, 139, blue, 3)
text(80, 144, "Radius 2 primary", 14, blue, 600)
line(282, 139, 312, 139, grey, 2)
text(322, 144, "Radius 3 sensitivity, same r2-selected prefixes", 14, grey)
text(40, 184, "Case / global ZYX origin", 14, weight=700)
text(368, 184, "Same-chain continuity change", 14, weight=700)
text(902, 175, "Radius 2 switches", 14, weight=700)
text(902, 195, "DP / baseline", 13, grey)
for tick in [-8, -4, 0, 4, 8]:
    line(axis(tick), 214, axis(tick), 530, ink if tick == 0 else guide, 1.4 if tick == 0 else 1)
    line(axis(tick), 566, axis(tick), 686, ink if tick == 0 else guide, 1.4 if tick == 0 else 1)
    text(axis(tick), 738, f"{tick:+d}%" if tick else "0%", 13, grey, anchor="middle")
text(40, 219, "Development", 15, weight=700)
text(40, 551, "Spatial validation", 15, weight=700)
text(368, 551, "Public source / parameter freeze: 1afa30ab", 13, grey)
ys = [254, 330, 406, 482, 594, 670]
for case, y in zip(cases, ys):
    scroll, z, yy, x, _ = case.split("_")
    text(40, y - 4, f"Scroll {scroll[1:]}", 16, weight=700)
    text(40, y + 18, f"{z}z / {yy}y / {x}x", 13, grey)
    for radius, dy, color in [(2, -7, blue), (3, 13, grey)]:
        pair = [lookup[case, radius, b] for b in ("below", "above")]
        values = [100 * (r["dp"]["continuity"] / r["baseline"]["continuity"] - 1) for r in pair]
        a, b = map(axis, values)
        line(a, y + dy, b, y + dy, color, 2)
        parts.append(f'<circle cx="{b:.3f}" cy="{y+dy}" r="6" fill="white" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<circle cx="{a:.3f}" cy="{y+dy}" r="3.8" fill="{color}"/>')
        label = f"{values[0]:+.2f}%" if abs(values[0] - values[1]) < .005 else f"{values[0]:+.2f}% / {values[1]:+.2f}%"
        text((a+b)/2, y - 20 if radius == 2 else y + 37, label, 12, color, anchor="middle")
    for bracket, dy in [("below", -2), ("above", 18)]:
        row = lookup[case, 2, bracket]
        text(902, y + dy, f'{bracket}: {row["dp"]["interior_switches"]} / {row["baseline"]["interior_switches"]}', 13, grey)
text(616, 764, "Relative change vs the corresponding mature-baseline prefix", 13, grey, anchor="middle")
text(40, 790, "Filled / open markers are the lower / upper whole-curve coverage brackets.", 14, grey)
text(40, 814, "Radius 3 reuses radius 2 prefixes; coverage changes are in the complete report.", 14, grey)
text(40, 838, "New-case error counts hold steady. Boundary switches are zero in all plotted pairs.", 14, grey)
text(40, 862, "Scope: partial manual sustained-known support. Surface quality is a later stage.", 14, grey)
text(40, 886, "Source: EduceLab-Scrolls (Parsons et al., 2023); pinned villa cleanup and fiber_hz_vt.", 13, grey)
parts.append('</g></svg>')
output = ROOT / "centre-path-comparison.svg"
output.write_text("\n".join(parts) + "\n")
import xml.etree.ElementTree as ET
ET.parse(output)
print(json.dumps({"status": "passed", "cases": 6, "development": 4, "spatial_validation": 2,
                  "plotted_pair_count": len(rows), "source": "published aggregates only", "new_metric_calls": 0}))
