# Imprinting

Imprinting ensures shared surfaces between adjacent volumes are meshed consistently. It's enabled by default.

## What is Imprinting?

When two volumes share a surface (e.g., two boxes touching), imprinting:

1. Identifies the shared surface
2. Creates matching mesh elements on both sides
3. Ensures particles can cross the boundary correctly

Without imprinting, adjacent volumes might have incompatible meshes at their interface, causing particle tracking errors.

## Default Behavior

All three export methods, `export_dagmc_h5m_file`,
`export_unstructured_mesh_file`, and `export_gmsh_mesh_file`, accept the same
`imprint` configuration. Omitting it uses an immutable default mapping with the
contents `{"threads": "all", "glue": "partial"}`:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

To enable imprinting explicitly, provide a mapping containing **exactly both**
`"threads"` and `"glue"`. Missing or additional keys are rejected; partial
configurations are not merged with defaults. Caller mappings are never modified.

| Entry | Accepted values | Default |
|-------|-----------------|---------|
| `"threads"` | `"all"` or a positive Python `int`; booleans are not accepted | `"all"` |
| `"glue"` | `"partial"`, `"full"`, or `None` | `"partial"` |

The mesher backend receives the mapping directly, matching the API of the pinned
dependency `cad-to-dagmc-mesher==0.3.5`. GMSH uses the same validated options.

## Disabling Imprinting

For geometries that don't need it, use the literal `False` instead of a mapping:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint=False,
)
```

## Limiting the Threads Used by Imprinting

Imprinting runs in parallel and its peak RAM scales with the number of threads.
Large models can run out of memory when imprinting on all logical processors.
Set `"threads"` to a positive integer while still supplying `"glue"`:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint={"threads": 1, "glue": "partial"},  # Lower peak RAM
)
```

One thread generally uses less memory at the cost of speed. Larger positive
integers trade memory for parallelism, for example
`imprint={"threads": 4, "glue": "partial"}`.

`"threads": "all"` actively requests the OpenCASCADE logical processor count,
`max(1, OSD_Parallel.NbLogicalProcessors_s())`. It does not inherit a previously
limited pool. Both `"all"` and explicit integer counts apply only during
imprinting. The previous pool size is restored afterwards, including on errors,
so subsequent meshing and CadQuery operations retain their own thread settings.
Zero, negative integers, booleans, floats, `None`, and strings other than
`"all"` are invalid thread values.

## Choosing the Imprint Glue

The boolean operations behind imprinting can be told how the solids are expected
to meet, which lets them skip work. Set this with `imprint["glue"]`. On CadQuery
with the selectable glue API, the value is passed through to its imprint:

| `imprint["glue"]` | What it does | Use when |
|----------------|--------------|----------|
| `"partial"` (default) | Fastest and lowest RAM | Solids touch or share faces, fully or in part, without any faces crossing or solids overlapping |
| `"full"` | Does not intersect edges or faces at all | Shared whole faces coincide exactly. Faces that only partly coincide are not split |
| `None` | Glue off, a full general-fuse intersection. The slowest | A general intersection is needed rather than glue assumptions; input solids must still not overlap |

Note the name `"full"` is counterintuitive: it is the *least* thorough option, as it assumes the faces already match. For the most thorough imprint use `None`.

Disabling glue does not make overlapping solids valid DAGMC geometry. Overlaps
still have no unique material and are rejected; repair them in the CAD model.

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint={"threads": 4, "glue": None},  # Requires selectable CadQuery glue
)
```

### CadQuery version compatibility

Both CadQuery **2.8.0** and the latest **master** are supported and tested.
Glue support was added in [CadQuery/cadquery#2069](https://github.com/CadQuery/cadquery/pull/2069). The installed API is checked rather than relying on a version string.

| `imprint["glue"]` | CadQuery 2.8.0 | CadQuery master with the glue API |
|---|---|---|
| `"partial"` (default) | Legacy imprint already uses partial glue, without a fallback warning | Exact `"partial"` option |
| `"full"` | On multi-solid geometry, `RuntimeError` before imprinting or writing output, with the installed version and upgrade advice | Exact `"full"` option |
| `None` | On multi-solid geometry, `RuntimeError` before imprinting or writing output: the legacy API cannot disable partial glue | Exact `None` option, leaving glue off |

CadQuery 2.8.0 uses `BOPAlgo_MakeConnected`, which internally hard-codes
[`BOPAlgo_GlueShift` (partial glue)](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BOPAlgo/BOPAlgo_MakeConnected.cxx).
Calling its imprint without a `glue` keyword therefore uses partial glue, not
no glue. On current master, omitting `glue` also selects partial, whereas
explicit `glue=None` leaves the builder in `GlueOff` mode. Neither `"full"`
nor `None` can be honoured by the legacy API, so they fail rather than
silently using partial glue.

`imprint=False` disables the operation and supplies no glue or thread options.
With a single solid, a valid mapping is still checked, but the actual imprint
is skipped, so all three valid glue modes can be used even on the legacy API.
Invalid mapping keys, thread values, or glue values are always rejected,
including for a single solid. Both meshing backends follow these rules.

## Migrating from the Previous API

| Previous call | Replacement |
|---------------|-------------|
| `imprint=True` | Omit `imprint`, or use `imprint={"threads": "all", "glue": "partial"}` |
| `imprint=1` | `imprint={"threads": 1, "glue": "partial"}` |
| `imprint=False` | Unchanged |

The old `True` and integer shorthands are no longer accepted; `imprint=None` is
also invalid. Move any separate `imprint_glue` value into the mapping's `"glue"`
entry and always include `"threads"`. There is no compatibility shim or separate
glue keyword. Only omission selects the immutable default; passing an empty or
incomplete mapping is an error.

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

Peak RAM is usually the limit rather than time. If imprinting runs out of memory,
try `imprint={"threads": 1, "glue": "partial"}` before reaching for
`imprint=False`, which changes the resulting geometry.

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
    imprint={"threads": "all", "glue": "partial"},  # Also the default
)
```

## Meshing Geometry You Imprinted Yourself

If you need more control over the imprint than cad_to_dagmc gives you, for
example a fuzzy tolerance or a tool other than
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
