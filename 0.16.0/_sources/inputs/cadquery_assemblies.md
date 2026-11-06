# CadQuery Assemblies

CadQuery assemblies provide a structured way to organize multi-part geometry. They offer special features for automatic material tagging based on part names or materials.

## Basic Assembly

Create an assembly and add parts:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create shapes
sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

# Create assembly
assembly = cq.Assembly()
assembly.add(sphere)
assembly.add(small_sphere)

# Convert with manual tags
model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1", "mat2"])
model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)
```

## Using Assembly Names as Material Tags

Name your assembly parts and use those names automatically as material tags:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")      # Name becomes material tag
assembly.add(small_sphere, name="steel")   # Name becomes material tag

model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_names"  # Use part names as tags
)
model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)
```

:::{note}
Parts without explicit names will receive auto-generated UUIDs as material tags.
Always name your parts to ensure meaningful material tags.
:::

## Using Assembly Materials as Tags

CadQuery 2.6.1+ supports `cq.Material` objects. Use these for material tagging:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere, name="sphere", material=cq.Material("tungsten"))
assembly.add(small_sphere, name="small_sphere", material=cq.Material("steel"))

model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_materials"  # Use Material objects as tags
)
model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)
```

:::{warning}
This feature requires CadQuery > 2.6.1. All parts in the assembly must have materials assigned, or a `ValueError` will be raised.
:::

## Assemblies with Mesh Parameters

Assemblies work well with per-volume mesh sizing using the `set_size` parameter:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create boxes with different intended mesh resolutions
coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
default_box = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(coarse_box, name="coarse")
assembly.add(fine_box, name="fine")
assembly.add(default_box, name="default")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

# Use material tag names in set_size
model.export_dagmc_h5m_file(
    filename="different_resolution_meshes.h5m",
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,  # Coarse mesh for this material
        "fine": 0.1,    # Fine mesh for this material
        # "default" not specified - uses global min/max
    },
)
```

## Nested Assemblies

cad_to_dagmc handles nested (hierarchical) assemblies automatically:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create sub-assemblies
fuel_assembly = cq.Assembly()
fuel_assembly.add(cq.Workplane().cylinder(10, 1), name="fuel_pin_1")
fuel_assembly.add(cq.Workplane().moveTo(3, 0).cylinder(10, 1), name="fuel_pin_2")

coolant = cq.Workplane().box(20, 20, 12)

# Create main assembly with nested assembly
main_assembly = cq.Assembly()
main_assembly.add(fuel_assembly, name="fuel")  # Nested assembly
main_assembly.add(coolant, name="coolant")

model = CadToDagmc()
model.add_cadquery_object(main_assembly, material_tags="assembly_names")
model.export_dagmc_h5m_file()
```

The nested assembly's leaf solids are extracted and tagged appropriately.

## Assembly Tagging Options Comparison

| Option | Source | Example | Notes |
|--------|--------|---------|-------|
| Manual list | Explicit | `["mat1", "mat2"]` | Order must match volumes |
| `"assembly_names"` | Part names | Uses `name="..."` | Auto UUIDs for unnamed parts |
| `"assembly_materials"` | Material objects | Uses `material=cq.Material("...")` | Requires CadQuery > 2.6.1 |

## See Also

- [Assembly Names](../material_tagging/assembly_names.md) - Detailed guide on using assembly names
- [Assembly Materials](../material_tagging/assembly_materials.md) - Detailed guide on using assembly materials
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Control mesh density per volume
