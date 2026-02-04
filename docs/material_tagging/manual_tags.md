# Manual Material Tags

The most explicit method - provide a list of material names matching the order of volumes.

## Basic Usage

Specify tags as a list of strings:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane("XY").sphere(10)
box = cq.Workplane("XY").box(20, 20, 20).translate((30, 0, 0))

assembly = cq.Assembly()
assembly.add(sphere)
assembly.add(box)

model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags=["tungsten", "steel"]  # Order matters!
)
model.export_dagmc_h5m_file()
```

The first tag is assigned to the first volume, second to second, and so on.

## Single Volume

For a single volume, use a list with one element:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane("XY").moveTo(100, 0).sphere(5)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=sphere, material_tags=["mat1"])
model.export_dagmc_h5m_file()
```

## Multiple Volumes with Same Material

Use the same tag for multiple volumes:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create 5-letter text (5 volumes)
text = cq.Workplane("XY").text("DAGMC", 10, 2)

model = CadToDagmc()
# All letters get the same material
model.add_cadquery_object(text, material_tags=["letter"] * 5)
model.export_dagmc_h5m_file()
```

## With STEP Files

STEP files can use manual tags or automatic tagging from assembly structure:

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()

# Option 1: Manual tags
model.add_stp_file(
    filename="geometry.step",
    material_tags=["mat1", "mat2", "mat3"]  # Must match volume count
)

# Option 2: If STEP was saved from a named assembly
model.add_stp_file(
    filename="geometry.step",
    material_tags="assembly_names"  # Extract names from STEP structure
)
```

See [STEP Files](../inputs/step_files.md) for more details on using assembly names with STEP files.

## Reserved Tag Names

:::{warning}
**Do not use `"vacuum"` as a material tag.** DAGMC and OpenMC treat volumes tagged with `"vacuum"` as true vacuum (void space). Particles entering a vacuum region will be lost. If you need to model low-density gas, use a different name like `"air"` or `"helium"`.
:::

## Multiple Additions

When adding multiple objects separately, each needs its own tags:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

box = cq.Workplane("XY").moveTo(2, 0).box(2, 2, 2)
cylinder = cq.Workplane("XY").box(2, 1, 1)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=box, material_tags=["mat1"])
model.add_cadquery_object(cadquery_object=cylinder, material_tags=["mat2"])
model.export_dagmc_h5m_file()
```

## Determining Volume Count

If you're unsure how many volumes are in your geometry:

```python
import cadquery as cq

# For CadQuery objects
shape = cq.Workplane("XY").text("HELLO", 10, 2)
num_volumes = len(shape.val().Solids())
print(f"Shape has {num_volumes} volumes")

# For STEP files
imported = cq.importers.importStep("geometry.step")
num_volumes = len(imported.val().Solids())
print(f"STEP file has {num_volumes} volumes")
```

## Using Tags with set_size

Material tag names can be used in the `set_size` parameter for per-volume mesh sizing:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)

assembly = cq.Assembly()
assembly.add(coarse_box)
assembly.add(fine_box)

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["coarse_mat", "fine_mat"])

# Reference material tags in set_size
model.export_dagmc_h5m_file(
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse_mat": 0.9,  # Use tag name
        "fine_mat": 0.1,    # Use tag name
    },
)
```

## Error Handling

:::{warning}
The number of material tags must exactly match the number of volumes:

```python
# This will raise an error - 2 volumes but only 1 tag
model.add_cadquery_object(assembly, material_tags=["mat1"])
# ValueError: Number of material tags (1) does not match number of volumes (2)
```
:::

## See Also

- [Assembly Names](assembly_names.md) - Automatic tagging from part names
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Using tags for mesh control
