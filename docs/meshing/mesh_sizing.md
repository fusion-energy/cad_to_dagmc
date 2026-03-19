# Per-Volume Mesh Sizing

Control mesh density for different volumes using the `set_size` parameter. This allows finer meshes where detail is needed and coarser meshes elsewhere.

:::{note}
Per-volume mesh sizing only works with the **GMSH backend**. The CadQuery backend ignores `set_size`.
:::

## Basic Usage

Specify mesh sizes for specific volumes:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
default_box = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(coarse_box, name="coarse")
assembly.add(fine_box, name="fine")
assembly.add(default_box, name="global")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

# Check available material tags
print("Material tags:", model.material_tags)
# Output: Material tags: ['coarse', 'fine', 'global']

model.export_dagmc_h5m_file(
    filename="different_resolution_meshes.h5m",
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,  # Coarse mesh for this volume
        "fine": 0.1,    # Fine mesh for this volume
        # "global" not specified - uses min/max only
    },
)
```

## Specifying Volumes

### By Material Tag Name

Use material tag names (recommended):

<!--pytest-codeblocks:skip-->
```python
set_size={
    "fuel": 0.5,      # All volumes with "fuel" tag
    "coolant": 2.0,   # All volumes with "coolant" tag
}
```

### By Volume ID

Use integer volume IDs:

<!--pytest-codeblocks:skip-->
```python
set_size={
    1: 0.5,  # Volume 1
    2: 5.0,  # Volume 2
    3: 1.0,  # Volume 3
}
```

### Mixed

Combine both approaches:

<!--pytest-codeblocks:skip-->
```python
set_size={
    1: 0.5,           # Volume 1 specifically
    "coolant": 2.0,   # All coolant volumes
}
```

## How It Works

1. Volumes not in `set_size` use `min_mesh_size` and `max_mesh_size` only
2. Volumes in `set_size` get their specified target size
3. Material tag names are resolved to all volumes with that tag
4. The mesh size applies to all surfaces of the volume

## Complete Example

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create geometry with different mesh requirements
shield_inner = cq.Workplane("XY").sphere(5)
shield_outer = cq.Workplane("XY").sphere(10).cut(cq.Workplane("XY").sphere(5))
casing = cq.Workplane("XY").box(25, 25, 25).cut(cq.Workplane("XY").sphere(10))

assembly = cq.Assembly()
assembly.add(shield_inner, name="shield_inner")
assembly.add(shield_outer, name="shield_outer")
assembly.add(casing, name="casing")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

# Fine mesh on inner shield (where neutrons interact most)
# Coarse mesh on casing (less important)
# Default mesh on outer shield
model.export_dagmc_h5m_file(
    filename="shielding.h5m",
    min_mesh_size=0.1,
    max_mesh_size=5.0,
    set_size={
        "shield_inner": 0.2,  # Fine mesh
        "casing": 3.0,        # Coarse mesh
        # "shield_outer" uses global min/max
    },
)
```

## Using with Volume Meshes

`set_size` also works with volume mesh export:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
default_box = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(coarse_box, name="coarse")
assembly.add(fine_box, name="fine")
assembly.add(default_box, name="global")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

# GMSH mesh file with per-volume sizing
model.export_gmsh_mesh_file(
    filename="different_resolution_meshes.msh",
    dimensions=2,
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,
        "fine": 0.1,
    },
)
```

## Tips

:::{tip}
**Finding volume IDs**: If using volume IDs instead of tag names, the order depends on how volumes were added. Using material tag names is more robust.
:::

:::{tip}
**Checking tags**: After adding geometry, check `model.material_tags` to see available tag names:

<!--pytest-codeblocks:skip-->
```python
model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")
print(model.material_tags)
```
:::

## See Also

- [GMSH Backend](gmsh_backend.md) - Full meshing backend documentation
- [Assembly Names](../material_tagging/assembly_names.md) - Using assembly names for tags
