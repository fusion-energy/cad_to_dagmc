# Geometry Scaling

`scale_factor` scales the geometry about the origin. OpenMC and most other
neutronics codes work in centimetres, while CAD tools usually save in
millimetres, so the most common value is 0.1. CadQuery reads a STEP file in
millimetres whatever unit it was saved in, so 0.1 gives centimetres for any
STEP file.

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Modelled in mm
sphere = cq.Workplane().sphere(50)
small_sphere = cq.Workplane().moveTo(100, 0).sphere(20)

assembly = cq.Assembly()
assembly.add(sphere)
assembly.add(small_sphere)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1", "mat2"])

# mm to cm, so the spheres have radii of 5 cm and 2 cm in the h5m file
model.export_dagmc_h5m_file(filename="dagmc.h5m", scale_factor=0.1)
```

## Common Scale Factors

| From | To | Scale Factor |
|------|-----|-------------|
| mm | cm | 0.1 |
| mm | m | 0.001 |
| cm | mm | 10.0 |
| m | cm | 100.0 |
| inch | cm | 2.54 |
| foot | cm | 30.48 |

## Scaling at Different Stages

`add_cadquery_object()` and `add_stp_file()` take a `scale_factor`, and so do
the three export methods. The two multiply. Adding scales the stored solids
and exporting scales them again, so a box added with `scale_factor=0.1` and
exported with `scale_factor=10` comes out at its original size.

Use one or the other. Scaling as you add suits sources in different units
(next section). Scaling at export, as in Basic Usage, applies one factor to
everything.

[`check_overlaps()`](overlaps.md#checking-every-pair) scales the stored solids
in the same way, so give it the `scale_factor` you export with, not the one you
added with.

## Different Scales for Different Parts

Sources in different units each take their own `scale_factor` when added:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Stands in for a STEP file from a CAD tool, in mm
cq.Workplane().box(300, 300, 300).export("component_in_mm.step")

model = CadToDagmc()

# STEP file in mm
model.add_stp_file(
    filename="component_in_mm.step",
    material_tags=["steel"],
    scale_factor=0.1,  # Convert mm to cm
)

# CadQuery object in cm (no scaling needed), beside the 30 cm box
sphere = cq.Workplane().sphere(10).translate((40, 0, 0))  # 10 cm radius
model.add_cadquery_object(
    cadquery_object=sphere,
    material_tags=["tungsten"],
    scale_factor=1.0,  # No scaling
)

model.export_dagmc_h5m_file(filename="combined.h5m")
```

## Mesh Size and Scaling

The geometry is scaled before it is meshed, so every linear sizing argument is
in the units of the scaled geometry. On the Gmsh backend these are
`min_mesh_size`, `max_mesh_size` and `set_size`. On the cad-to-dagmc-mesher
backend they are `tolerance` and `target_edge_length`. `angular_tolerance` is
an angle, in radians, and does not change with scaling.

With `scale_factor=100` (a model built in metres), the default `tolerance` of
0.5 is a 5 mm deflection on the output, not 0.5 m. So a fixed size gets finer
relative to the CAD as `scale_factor` grows, and on a large model the mesh may
not fit in RAM. Scale the sizes along with the geometry.

For CAD in millimetres exported in centimetres:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_cadquery_object(cq.Workplane().sphere(100), material_tags=["steel"])  # mm

# cad-to-dagmc-mesher backend: a 0.1 cm (1 mm) chordal deflection
model.export_dagmc_h5m_file(filename="mesher.h5m", scale_factor=0.1, tolerance=0.1)

# Gmsh backend: elements between 0.5 cm and 2 cm
model.export_dagmc_h5m_file(
    filename="gmsh.h5m", scale_factor=0.1, min_mesh_size=0.5, max_mesh_size=2.0
)
```

## See Also

- [STEP Files](../inputs/step_files.md): `scale_factor` on `add_stp_file()`
- [CadQuery Objects](../inputs/cadquery_objects.md): `scale_factor` on `add_cadquery_object()`
