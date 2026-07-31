#!/usr/bin/env python3
"""Generate the project-local VEMD10940FX01 clearance/orientation STEP model."""

from pathlib import Path

import cadquery as cq

OUT = Path(__file__).with_name("VEMD10940FX01.step")

# Datasheet envelope: 3.0 mm x 2.0 mm x 1.0 mm.  The rear package occupies
# y=0..1 mm and the side-looking molded lens occupies y=-1..0 mm.
package = (
    cq.Workplane("XY")
    .box(3.0, 1.0, 1.0, centered=(True, True, False))
    .translate((0.0, 0.5, 0.0))
)
lens_full = (
    cq.Workplane("YZ")
    .center(0.0, 0.5)
    .ellipse(1.0, 0.5)
    .extrude(1.1, both=True)
)
lens = lens_full.intersect(
    cq.Workplane("XY")
    .box(2.2, 1.0, 1.0, centered=(True, True, False))
    .translate((0.0, -0.5, 0.0))
)

# Visible metallization and die are included so polarity and optical direction
# remain obvious in KiCad's 3D viewer.  They do not enlarge the package envelope.
cathode = (
    cq.Workplane("XY")
    .box(0.40, 1.00, 0.04, centered=(True, True, False))
    .translate((-1.30, 0.50, 0.0))
)
anode = (
    cq.Workplane("XY")
    .box(0.40, 1.00, 0.04, centered=(True, True, False))
    .translate((1.30, 0.50, 0.0))
)
die = (
    cq.Workplane("XY")
    .box(0.48, 0.08, 0.30, centered=(True, True, False))
    .translate((0.0, -0.02, 0.35))
)

assembly = cq.Assembly(name="VEMD10940FX01")
assembly.add(package, name="package", color=cq.Color(0.08, 0.08, 0.09))
assembly.add(lens, name="daylight_filter_lens", color=cq.Color(0.12, 0.05, 0.16, 0.78))
assembly.add(cathode, name="cathode", color=cq.Color(0.72, 0.72, 0.74))
assembly.add(anode, name="anode", color=cq.Color(0.72, 0.72, 0.74))
assembly.add(die, name="photodiode_die", color=cq.Color(0.20, 0.35, 0.48))
assembly.save(str(OUT), exportType="STEP", mode="default")
print(OUT)
