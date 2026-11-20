# Checking for Overlaps

DAGMC gives every region exactly one material, so two solids that occupy the
same space are invalid however well they mesh. A region claimed by two solids
transports through whichever volume DAGMC resolves first. The file is
watertight and nothing looks wrong, but tallies there are scored in the wrong
material, and particles can be lost.

## What exporting checks

With the cad-to-dagmc-mesher backend (the default for
`export_dagmc_h5m_file()`), exporting runs the overlap checks that cost nothing
and refuses two kinds of overlap with a `ValueError` that names the solids:

- overlaps along coincident faces, which the imprint splits and records, such
  as a face pressed slightly into its neighbour or two boxes overlapping;
- solids the imprint swallows into another, such as a sphere left inside a box
  that should have had it cut out.

After meshing it also prints a warning where the meshes of two solids
penetrate each other.

These checks do not see every overlap. Two intersecting spheres, or a rod
pushed through a box, have no coincident faces and neither swallows the other,
so they export with only the warning. Both refusals come from the imprint, so
with `imprint=False` only the warning is left. The Gmsh backend runs none of
these checks and writes overlapping solids without an error.

One check runs when the geometry is added rather than exported, whatever the
backend or `imprint`: `add_cadquery_object()` raises a `ValueError` naming the
parts if the same solid is in two of them, or was already added to the model
by an earlier call. Imprinting overlapping parts with
CadQuery's `Assembly.imprint` leaves them like that, with the region they share
in both, so this catches those overlaps in an assembly you imprinted yourself
and export with `imprint=False`.

## Checking every pair

`check_overlaps` intersects every pair of solids whose bounding boxes overlap,
exactly, and reports what each pair shares: how much, where, and whether it is
a thin layer along a contact surface. Exporting does not run it, because on a
large model it can take hours. It needs cad-to-dagmc-mesher, whichever meshing
backend you export with, and raises `CadToDagmcMesherNotFoundError` without it.

Run it yourself on CAD you have not checked, with the `scale_factor` you will
export with:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

block = cq.Workplane().box(100, 100, 50).translate((0, 0, -25))
# meant to sit on the block, but modelled 0.01 into it
slab = cq.Workplane().box(100, 100, 10).translate((0, 0, 4.99))
ball = cq.Workplane().sphere(5).translate((0, 0, 12))

model = CadToDagmc()
model.add_cadquery_object(block, material_tags=["steel"])
model.add_cadquery_object(slab, material_tags=["water"])
model.add_cadquery_object(ball, material_tags=["tungsten"])

report = model.check_overlaps()
print(report)
assert not report.clean
```

It prints each overlap as it finds it:

```text
Checking 2 solid pair(s) whose bounding boxes overlap...
  found: 'steel (solid 0)' and 'water (solid 1)' overlap by 100 cm³ along a contact surface (0.020% of 'steel (solid 0)', 0.1% of 'water (solid 1)'): a layer about 0.01 cm thick, spanning 100 x 100 x 0.01 cm around (0, 0, -0.005)
  found: 'water (solid 1)' and 'tungsten (solid 2)' overlap by 112 cm³ (0.1% of 'water (solid 1)', 21.5% of 'tungsten (solid 2)'), spanning 9.16 x 9.16 x 2.99 cm around (0, 0, 8.495)
Done in 0.0 min: 2 overlapping, 0 failed, 0 unchecked.
```

`print(report)` then lists the overlaps again, with advice on fixing them.

`report.overlaps` holds the pairs, largest first. Each has `name_a` and
`name_b` (the material tag and the solid's position in the model), `shared` (the
shared volume, in cm³ after `scale_factor`), `thickness`, `box` (the shared
region's bounding box) and `is_contact_layer`. `report.clean` is `True` only
when every pair was checked and none overlaps. Pairs OpenCASCADE could not
intersect are listed in `report.failed`, and `report.unchecked` counts the pairs
that `max_seconds` left out.

The full signature is `check_overlaps(scale_factor=1.0, *, material_tags=None,
max_seconds=None, progress=True)`. Pass `progress=False` to turn the printing
off.

## Fixing what it finds

Compare an overlap's thickness with the meshing tolerance. A layer far thinner
than the faceting is modelling slack that does not change transport; one solid
sunk into another does. To fix an overlap in the CAD:

- boolean-subtract one solid from the other, so they share a surface instead of
  a volume (`water = water.cut(steel)`);
- or, for a layer along a contact surface, move the face that was pressed into
  its neighbour back to the contact.

To export the rest of the model while you fix it, leave out one solid of each
overlapping pair.

## How long it takes

Each pair costs from well under a second (boxes and other simple shapes) to
over an hour (large imported B-spline solids that touch). GEOUNED's 153-solid
`SCDR.stp` takes 26 s for its 522 pairs. On a 108-solid imported model, 1,408 pairs
survive the bounding-box cull, disjoint pairs take about 15 s each, and one
pair of touching solids took 1 h 44 min. To spend that time where it matters:

<!--pytest-codeblocks:skip-->
```python
# only the pairs involving solids tagged "blanket", against every solid
report = model.check_overlaps(material_tags=["blanket"])

# stop starting new pairs after ten minutes; the report counts the rest
report = model.check_overlaps(max_seconds=600)
```

A tag in `material_tags` that no solid has raises `ValueError`.
