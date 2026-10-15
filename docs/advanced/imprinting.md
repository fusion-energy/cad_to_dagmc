# Imprinting

Imprinting ensures shared surfaces between adjacent volumes are meshed consistently. It's enabled by default.

## What is Imprinting?

When two volumes share a surface (e.g., two boxes touching), imprinting:

1. Identifies the shared surface
2. Creates matching mesh elements on both sides
3. Ensures particles can cross the boundary correctly

Without imprinting, adjacent volumes might have incompatible meshes at their interface, causing particle tracking errors.

## Default Behavior

Imprinting is enabled by default for all three export methods. Omitting `imprint`
uses `{"threads": "all", "glue": "partial"}`:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint={"threads": "all", "glue": "partial"},  # Default
)
```

Explicit dictionaries require exactly the two keys below; partial configurations
are not merged with defaults. Caller dictionaries are never modified.

| Entry | Accepted values | Default |
|-------|-----------------|---------|
| `"threads"` | `"all"` or a positive Python `int`; booleans are not accepted | `"all"` |
| `"glue"` | `"partial"`, `"full"`, or `None` | `"partial"` |

## Disabling Imprinting

For geometries that don't need it, use `imprint=False`:

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

`"threads": "all"` requests all OpenCASCADE logical processors, even if the
current pool is limited. On both backends, thread settings apply only during
imprinting; the previous pool size is restored afterwards, including on errors.
Meshing and later CadQuery operations keep their own thread settings.

## Choosing the Imprint Glue

Set `imprint["glue"]` according to how the solids meet:

| `imprint["glue"]` | What it does | Geometry requirement |
|----------------|--------------|----------|
| `"partial"` (default) | Glues fully or partly coincident faces | Touching solids without crossing faces or overlaps |
| `"full"` | Skips edge and face intersections | Shared whole faces must coincide exactly; partly coincident faces are not split |
| `None` | No glue; runs general intersection checks | Geometry requiring general intersection rather than glue assumptions |

`None` means **glue off**, not "use the default". Imprinting still runs.
On CadQuery with selectable glue, omitting its `glue` argument defaults to
`"partial"`; explicitly passing `glue=None` disables the glue optimisation.
Likewise, omitting this package's `imprint` argument selects `"partial"`, while
`imprint=False` disables imprinting entirely.

Disabling glue does not make overlapping solids valid DAGMC geometry. Repair
overlaps in the CAD model before exporting.

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint={"threads": 4, "glue": None},  # Requires selectable CadQuery glue
)
```

### CadQuery version compatibility

CadQuery 2.8.0's legacy imprint always uses partial glue. On multi-solid
geometry, `"full"` and `None` raise `RuntimeError`; CadQuery master with the
selectable glue API supports all three modes. Support is detected from the
installed imprint signature, not the version string.

## Migrating from the Previous API

| Previous call | Replacement |
|---------------|-------------|
| `imprint=True` | Omit `imprint` |
| `imprint=1` | `imprint={"threads": 1, "glue": "partial"}` |
| `imprint=False` | Unchanged |

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
