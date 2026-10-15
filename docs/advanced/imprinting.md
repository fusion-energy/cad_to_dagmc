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

## Choosing the Imprint Glue

The boolean operations behind imprinting can be told how the solids are expected to meet, which lets them skip work. This is set with `imprint_glue`. On CadQuery master with the glue API, the option is passed straight through to CadQuery's imprint:

| `imprint_glue` | What it does | Use when |
|----------------|--------------|----------|
| `"partial"` (default) | Fastest and lowest RAM | Solids touch or share faces, fully or in part, without any faces crossing or solids overlapping |
| `"full"` | Does not intersect edges or faces at all | Shared faces coincide exactly. Faces that only partly coincide are not split |
| `None` | Glue off, a full general-fuse intersection. The slowest | Faces cross one another or solids overlap |

Note the name `"full"` is counterintuitive: it is the *least* thorough option, as it assumes the faces already match. For the most thorough imprint use `None`.

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint=4,          # imprint on 4 threads
    imprint_glue=None,  # full general-fuse intersection
)
```

`imprint_glue` is accepted by `export_dagmc_h5m_file`, `export_unstructured_mesh_file` and `export_gmsh_mesh_file` (keyword-only on the latter two), whichever meshing backend is used.

### CadQuery version compatibility

Both CadQuery **2.8.0** and the latest **master** are supported and tested.
Glue support was added in [CadQuery/cadquery#2069](https://github.com/CadQuery/cadquery/pull/2069). The installed API is checked rather than relying on a version string.

| `imprint_glue` | CadQuery 2.8.0 | CadQuery master with the glue API |
|---|---|---|
| `"partial"` (default) | Legacy imprint already uses partial glue, without a fallback warning | Exact `"partial"` option |
| `"full"` | `RuntimeError` with the installed version and upgrade advice, before imprinting or writing the output | Exact `"full"` option |
| `None` | `RuntimeError`: the legacy API cannot disable partial glue | Exact `None` option, leaving glue off |

CadQuery 2.8.0 uses `BOPAlgo_MakeConnected`, which internally hard-codes
[`BOPAlgo_GlueShift` (partial glue)](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BOPAlgo/BOPAlgo_MakeConnected.cxx).
Calling its imprint without a `glue` keyword therefore uses partial glue, not
no glue. On current master, omitting `glue` also selects partial, whereas
explicit `glue=None` leaves the builder in `GlueOff` mode. Neither `"full"`
nor `None` can be honoured by the legacy API, so they fail rather than
silently using partial glue.

All three valid values are ignored when `imprint=False` or only one solid is present. Invalid values still raise `ValueError`, even with imprinting disabled. Both meshing backends follow the same compatibility rules. The mesher backend translates these public arguments into cad-to-dagmc-mesher's `imprint={"threads": ..., "glue": ...}` configuration; a release with that dictionary API is required.

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

## Meshing Geometry You Imprinted Yourself

If you need more control over the imprint than cad_to_dagmc gives you, for
example a different glue option, a fuzzy tolerance, or a tool other than
CadQuery, you can imprint the geometry yourself, save it as a BREP file, and
mesh it with `imprint=False`.

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# A small box sitting on part of a big box's top face, so imprinting has to
# split that face
big = cq.Workplane("XY").box(10, 10, 10)
small = cq.Workplane("XY").transformed(offset=(0, 0, 7)).box(4, 4, 4)

assembly = cq.Assembly()
assembly.add(big)
assembly.add(small)

# Imprint however you like, here with CadQuery's own imprint
imprinted, _ = cq.occ_impl.assembly.imprint(assembly)
imprinted.exportBrep("imprinted.brep")

# Later, possibly in another script, load the imprinted geometry
model = CadToDagmc()
model.add_cadquery_object(
    cq.importers.importBrep("imprinted.brep"),
    material_tags=["big", "small"],
)

# The geometry is already imprinted, so do not imprint it again
model.export_dagmc_h5m_file(
    filename="pre_imprinted.h5m",
    imprint=False,
    meshing_backend="cad-to-dagmc-mesher",
    scale_factor=10,
)
```

This works because a BREP file keeps the topology the imprint created: the face
two solids share is stored once and referenced by both, which is what gives
the DAGMC surface between them a sense for each volume. Both the
cad-to-dagmc-mesher and GMSH backends support this, including with
`scale_factor`.

:::{warning}
Use BREP, not STEP. A STEP file stores each solid separately, so the shared
face comes back as two coincident copies, one per solid. With `imprint=False`
these become two one sided DAGMC surfaces rather than one surface shared by
both volumes, and particles crossing the interface are not handed to the
neighbouring volume. Nothing reports this, the file is written as normal.
:::

## See Also

- [GMSH Backend](../meshing/gmsh_backend.md) - Meshing options
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Using material tags vs volume IDs
