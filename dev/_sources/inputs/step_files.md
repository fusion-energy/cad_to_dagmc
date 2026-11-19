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

A list needs exactly one tag per volume in the file, or `add_stp_file()` raises `ValueError`. [Determining Volume Count](../material_tagging/manual_tags.md#determining-volume-count) shows how to count them.

CadQuery reads a STEP file in millimetres, whatever unit it was saved in, so `scale_factor=0.1` gives the centimetres OpenMC uses; see [Geometry Scaling](../advanced/geometry_scaling.md).

## Tags from Named STEP Parts

A STEP file stores the name of each part, and CadQuery also writes each part's `cq.Material` into it. So [`material_tags="assembly_names"`](../material_tagging/assembly_names.md) and [`material_tags="assembly_materials"`](../material_tagging/assembly_materials.md) work on a STEP file as they do on a CadQuery assembly:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")
assembly.add(box, name="steel")
assembly.export("my_assembly.step")

model = CadToDagmc()
model.add_stp_file(
    filename="my_assembly.step",
    material_tags="assembly_names",
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

:::{warning}
CadQuery's STEP reader takes a part whose name ends in `_part` to be the shape of the assembly above it, so `"assembly_names"` and `"assembly_materials"` leave that part out without an error. `add_stp_file()` returns the number of volumes it added, which shows when this happens. Rename such parts, or tag the file with a list.
:::

## Multiple STEP Files

Combine multiple STEP files into a single DAGMC model:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# two STEP files to load
result1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cq.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = cq.Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.export("two_connected_cubes.step")

sphere = cq.Workplane().moveTo(100, 0).sphere(5)
sphere_assembly = cq.Assembly()
sphere_assembly.add(sphere)
sphere_assembly.export("single_sphere.step")

model = CadToDagmc()
model.add_stp_file(
    filename="two_connected_cubes.step",
    material_tags=["mat1", "mat2"],  # This file has 2 volumes
)
model.add_stp_file(
    filename="single_sphere.step",
    material_tags=["mat3"],  # This file has 1 volume
)

model.export_dagmc_h5m_file()
```

STEP files and CadQuery objects can go in the same model, each with its own `scale_factor`; see [Different Scales for Different Parts](../advanced/geometry_scaling.md#different-scales-for-different-parts).

## API Reference

### `add_stp_file()`

| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | str | Path to the STEP file |
| `scale_factor` | float | Scales the geometry as it is read (default 1.0) |
| `material_tags` | list[str] or str | A list with one tag per volume, `"assembly_names"` or `"assembly_materials"`; see [Material Tagging](../material_tagging/index.md). The default, None, adds the volumes without tags, which `export_dagmc_h5m_file()` rejects |

`scale_factor` comes before `material_tags`, so pass `material_tags` by keyword. `add_stp_file()` returns the number of volumes added. Exact signatures are on the [API Reference](../api.md) page.

## See Also

- [Assembly Names](../material_tagging/assembly_names.md): tags from part names
- [Assembly Materials](../material_tagging/assembly_materials.md): tags from `cq.Material` objects
- [Geometry Scaling](../advanced/geometry_scaling.md): unit conversion, and mesh sizes in scaled units
- [Manual Tags](../material_tagging/manual_tags.md): lists of material tags
