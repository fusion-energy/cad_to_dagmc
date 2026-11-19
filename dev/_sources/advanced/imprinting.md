# Imprinting

Imprinting splits the faces of touching solids so that each contact region
becomes one face shared by both solids. That face is meshed once and written
to the h5m file as one DAGMC surface with a sense for each volume, so a
particle crossing it moves into the neighbouring volume. Without imprinting,
each solid keeps its own copy of the contact face, and the h5m file gets two
coincident one-sided surfaces that do not hand particles to the neighbour.

`export_dagmc_h5m_file()`, `export_unstructured_mesh_file()` and
`export_gmsh_mesh_file()` all imprint by default, whichever meshing backend
they use.

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

# The shared face becomes one surface with a sense for each box
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint="partial",  # the default
)
```

## Defaults and Disabling

| Argument | Values | Default |
|----------|--------|---------|
| `imprint` | `"partial"`, `"full"`, `None` (imprint with the glue off) or `False` (do not imprint) | `"partial"` |
| `imprint_threads` | `"all"` or a positive int; keyword-only | `"all"` |

`imprint=None` is not the default. It still imprints, with the glue turned off
(see [Choosing the Imprint Glue](#choosing-the-imprint-glue)). Only `False`
skips imprinting:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(filename="dagmc.h5m", imprint=False)
```

Turn it off only when no two solids touch, or when you have imprinted the
geometry yourself (below). A single solid is never imprinted, so it does not
need `imprint=False`. Turning imprinting off also turns off the
[overlap checks](overlaps.md#what-exporting-checks) that come with it.

Imprinting runs in parallel, and its peak RAM grows with the number of threads.
If it runs out of memory, try `imprint_threads=1` before `imprint=False`, which
changes the geometry; see
[Limiting Imprinting Threads](parallel_processing.md#limiting-imprinting-threads).

## Choosing the Imprint Glue

The glue mode tells OpenCASCADE how the solids meet, so it can skip
intersection work the geometry does not need.

| `imprint` | Use it when the solids | Notes |
|-----------|------------------------|-------|
| `"partial"` (default) | touch or share faces, fully or in part, with no faces crossing and no overlaps | Splits faces that coincide only in part |
| `"full"` | share faces that coincide exactly | Intersects no edges or faces, so it does less work than `"partial"` but does not split a face that coincides only in part |
| `None` | have faces that cross | Glue off, so a full general intersection. The slowest mode |

cad_to_dagmc needs CadQuery 2.8.0 or newer, and CadQuery 2.8.0 imprints with
partial glue only. On several solids, `"full"` and `None` raise `RuntimeError`
on both meshing backends. They need a CadQuery that includes
[cadquery#2069](https://github.com/CadQuery/cadquery/pull/2069); cad_to_dagmc
detects it from CadQuery's imprint function, not from the version number.

Turning the glue off does not make overlapping solids valid DAGMC geometry.
Fix overlaps in the CAD; see [Checking for Overlaps](overlaps.md).

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

This works because a BREP file keeps the topology the imprint created. The
face two solids share is stored once and referenced by both, which is what
gives the DAGMC surface between them a sense for each volume. Both the
cad-to-dagmc-mesher and Gmsh backends support this, including with
`scale_factor`.

:::{warning}
Use BREP, not STEP. A STEP file stores each solid separately, so the shared
face comes back as two coincident copies, one per solid. With `imprint=False`
these become two one-sided DAGMC surfaces rather than one surface shared by
both volumes, and particles crossing the interface are not handed to the
neighbouring volume. Nothing reports this. The file is written as normal.
:::

`imprint=False` also skips the overlap checks that come with the export's
imprint, so run `model.check_overlaps()` on the imprinted geometry first; see
[Checking every pair](overlaps.md#checking-every-pair).

## Imprinting and Material Tag Order

Imprinting can change the order of the volumes. cad_to_dagmc reorders the
material tags to match, so each tag stays with its solid. Volume IDs given to
`set_size` or `unstructured_volumes` are the IDs after imprinting, which may not
follow the order you added the solids in, so give material tags there instead.

## See Also

- [Gmsh Backend](../meshing/gmsh_backend.md): meshing options
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md): sizing by material tag or volume ID
