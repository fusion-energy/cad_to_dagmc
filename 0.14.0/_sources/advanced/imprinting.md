# Imprinting

Imprinting ensures shared surfaces between adjacent volumes are meshed consistently. It's enabled by default.

## What is Imprinting?

When two volumes share a surface (e.g., two boxes touching), imprinting:

1. Identifies the shared surface
2. Creates matching mesh elements on both sides
3. Ensures particles can cross the boundary correctly

Without imprinting, adjacent volumes might have incompatible meshes at their interface, causing particle tracking errors.

## Default Behavior

Imprinting is enabled by default:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint=True,  # Default
)
```

## Disabling Imprinting

For geometries that don't need it:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint=False,
)
```

## Limiting the Threads Used by Imprinting

Imprinting runs in parallel and its peak RAM scales with the number of threads. Large models can run out of memory when imprinting on all cores, so a positive int can be passed instead of `True` to imprint with that many threads:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint=1,  # imprint on a single thread, the lowest peak RAM
)
```

`imprint=1` uses the least memory and is the slowest, `imprint=True` uses all available cores and is the fastest. Values in between trade the two off, for example `imprint=4`.

Only the imprint is limited. The meshing that follows it keeps all its threads on every backend, and the thread count is restored once the imprint is done so the cadquery operations that follow are not limited either. Note that `imprint=0` is not accepted: `0` cannot be told apart from `False` in Python, so use `imprint=False` to turn imprinting off.

## When to Disable Imprinting

**Safe to disable when:**
- Single volume geometry
- Volumes don't touch (separated in space)
- All volumes are independent (no shared surfaces)

**Keep enabled when:**
- Adjacent volumes share surfaces
- Volumes are in contact
- You're unsure

## Performance Considerations

Imprinting can be computationally expensive for complex geometries with many touching volumes. Disabling it may speed up mesh generation, but only do so if you're certain volumes don't share surfaces.

Peak RAM is usually the limit rather than time. If imprinting runs out of memory, lower the thread count with `imprint=1` before reaching for `imprint=False`, which changes the resulting geometry.

## Imprinting and Material Tag Order

Imprinting may change the internal ordering of volumes. cad_to_dagmc handles this automatically, preserving the correct material tag assignments.

If you're using volume IDs in `set_size` or `unstructured_volumes`, be aware that imprinting may affect the volume numbering. Using material tag names instead of IDs is more robust.

## Example: Adjacent Boxes

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Two boxes sharing a face
box1 = cq.Workplane("XY").box(10, 10, 10)
box2 = cq.Workplane("XY").moveTo(10, 0).box(10, 10, 10)  # Adjacent to box1

assembly = cq.Assembly()
assembly.add(box1)
assembly.add(box2)

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1", "mat2"])

# Imprinting ensures the shared face is meshed consistently
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint=True,  # Important for adjacent volumes
)
```

## See Also

- [GMSH Backend](../meshing/gmsh_backend.md) - Meshing options
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Using material tags vs volume IDs
