# STEP Files

STEP (Standard for the Exchange of Product Data) files are an industry-standard CAD format. Use them to import geometry from external CAD software.

## Single STEP File

Load a STEP file and convert to DAGMC:

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_stp_file(
    filename="geometry.step",
    material_tags=["mat1", "mat2"]  # One tag per volume in the file
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

## Using Assembly Names from STEP Files

If your STEP file was created from a CadQuery assembly with named parts, you can automatically use those names as material tags:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create an assembly with named parts
sphere = cq.Workplane().sphere(5)
box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")  # Name will become material tag
assembly.add(box, name="steel")        # Name will become material tag
assembly.save("my_assembly.stp", exportType="STEP")

# Load the STEP file using assembly names
model = CadToDagmc()
model.add_stp_file(
    filename="my_assembly.stp",
    material_tags="assembly_names",  # Automatically extract names from STEP
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

## Using Assembly Materials from STEP Files

If your STEP file was created with `cq.Material` objects, you can use those as material tags:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create an assembly with materials
sphere = cq.Workplane().sphere(5)
box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

assembly = cq.Assembly()
assembly.add(sphere, name="sphere_part", material=cq.Material("gold"))
assembly.add(box, name="box_part", material=cq.Material("silver"))
assembly.save("my_assembly.stp", exportType="STEP")

# Load the STEP file using assembly materials
model = CadToDagmc()
model.add_stp_file(
    filename="my_assembly.stp",
    material_tags="assembly_materials",  # Extract materials from STEP
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

:::{note}
Using `assembly_materials` requires CadQuery > 2.6.1.
:::

## Multiple STEP Files

Combine multiple STEP files into a single DAGMC model:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create and save STEP files
result1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cq.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = cq.Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("two_connected_cubes.stp", exportType="STEP")

sphere = cq.Workplane().moveTo(100, 0).sphere(5)
sphere_assembly = cq.Assembly()
sphere_assembly.add(sphere)
sphere_assembly.save("single_sphere.stp", exportType="STEP")

# Load multiple STEP files
model = CadToDagmc()
model.add_stp_file(
    filename="two_connected_cubes.stp",
    material_tags=["mat1", "mat2"],  # This file has 2 volumes
)
model.add_stp_file(
    filename="single_sphere.stp",
    material_tags=["mat3"],  # This file has 1 volume
)

model.export_dagmc_h5m_file(
    max_mesh_size=1,
    min_mesh_size=0.5,
)
```

## Mixing STEP Files with CadQuery Objects

Combine STEP files and CadQuery objects in the same model:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create a CadQuery object
sphere = cq.Workplane().sphere(10)

model = CadToDagmc()

# Add STEP file (in mm)
model.add_stp_file(
    filename="component.step",
    material_tags=["steel"],
    scale_factor=0.1,  # Convert mm to cm
)

# Add CadQuery object (already in cm)
model.add_cadquery_object(
    cadquery_object=sphere,
    material_tags=["tungsten"],
)

model.export_dagmc_h5m_file(filename="combined.h5m")
```

## Scaling STEP Files

STEP files from CAD software often use different units. Use `scale_factor` to convert:

<!--pytest-codeblocks:skip-->
```python
model.add_stp_file(
    filename="geometry_in_mm.step",
    material_tags=["mat1"],
    scale_factor=0.1,  # mm to cm (for neutronics)
)
```

Common scale factors:
- `0.1` - mm to cm
- `0.01` - mm to m
- `10.0` - cm to mm
- `100.0` - m to cm

## API Reference

### `add_stp_file()`

<!--pytest-codeblocks:skip-->
```python
model.add_stp_file(
    filename,             # Path to the STEP file
    material_tags=None,   # List of tags, or "assembly_names"/"assembly_materials"
    scale_factor=1.0,     # Geometry scaling factor
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | str | Path to the STEP file |
| `material_tags` | list[str] or str | Material tags - either a list, `"assembly_names"`, or `"assembly_materials"` |
| `scale_factor` | float | Scale geometry by this factor (default: 1.0) |

## Tips

:::{tip}
**Counting volumes**: If you don't know how many volumes are in a STEP file, load it in CadQuery first:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq

shape = cq.importers.importStep("geometry.step")
num_volumes = len(shape.val().Solids())
print(f"File has {num_volumes} volumes")
```
:::

:::{warning}
When using a list of material tags, the number must exactly match the number of volumes in the STEP file, or an error will be raised.
:::

## See Also

- [Assembly Names](../material_tagging/assembly_names.md) - Using assembly names as tags
- [Assembly Materials](../material_tagging/assembly_materials.md) - Using cq.Material as tags
- [Geometry Scaling](../advanced/geometry_scaling.md) - More on unit conversion
- [Manual Tags](../material_tagging/manual_tags.md) - Material tag assignment
