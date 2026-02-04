# Geometry Scaling

Scale geometry using the `scale_factor` parameter. Useful when converting between units (e.g., mm to cm for neutronics).

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere)
assembly.add(small_sphere)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1", "mat2"])

# Scale geometry 10x (e.g., mm to cm)
model.export_dagmc_h5m_file(
    min_mesh_size=0.5,
    max_mesh_size=1.0e6,
    scale_factor=10.0,
)
```

## Scaling at Different Stages

### When Adding Geometry

Scale when adding CadQuery objects or STEP files:

<!--pytest-codeblocks:skip-->
```python
# Scale CadQuery object
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags=["mat1"],
    scale_factor=0.1,  # Scale down (mm to cm)
)

# Scale STEP file
model.add_stp_file(
    filename="geometry_in_mm.step",
    material_tags=["mat1"],
    scale_factor=0.1,  # Scale down (mm to cm)
)
```

### When Exporting

Scale at export time:

<!--pytest-codeblocks:skip-->
```python
# Scale at export
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    scale_factor=0.1,
)
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

## Different Scales for Different Parts

When combining geometry from different sources with different units:

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import CadToDagmc
import cadquery as cq

model = CadToDagmc()

# STEP file in mm
model.add_stp_file(
    filename="component_in_mm.step",
    material_tags=["steel"],
    scale_factor=0.1,  # Convert mm to cm
)

# CadQuery object in cm (no scaling needed)
sphere = cq.Workplane().sphere(10)  # 10 cm radius
model.add_cadquery_object(
    cadquery_object=sphere,
    material_tags=["tungsten"],
    scale_factor=1.0,  # No scaling
)

model.export_dagmc_h5m_file(filename="combined.h5m")
```

## Neutronics Unit Conventions

Most neutronics codes (OpenMC, MCNP, etc.) work in **centimeters**. If your CAD software uses millimeters (common in mechanical engineering), apply a scale factor of 0.1:

<!--pytest-codeblocks:skip-->
```python
# CAD created in mm, simulation needs cm
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    scale_factor=0.1,  # mm to cm
)
```

## Mesh Size and Scaling

:::{warning}
Mesh size parameters (`min_mesh_size`, `max_mesh_size`, `set_size`) are applied **after** scaling. Set them in the **output units**, not the input units.
:::

Example:
```python
# Geometry is 100mm sphere, scaling to cm
# Want 0.5 cm mesh size (not 5 mm)
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    scale_factor=0.1,      # mm to cm
    min_mesh_size=0.5,     # 0.5 cm (in output units)
    max_mesh_size=2.0,     # 2.0 cm (in output units)
)
```

## See Also

- [STEP Files](../inputs/step_files.md) - Scaling STEP file input
- [CadQuery Objects](../inputs/cadquery_objects.md) - Scaling CadQuery input
