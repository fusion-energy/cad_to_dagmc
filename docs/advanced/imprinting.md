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

<!-- TODO once a CadQuery release includes Assembly.imprint
(CadQuery/cadquery#2128), name that release here instead of the PR. The
examples below skip themselves until the installed CadQuery has it. -->

### Imprinting an Assembly in Memory

CadQuery's `Assembly.imprint`, from
[cadquery#2128](https://github.com/CadQuery/cadquery/pull/2128) and not yet in
a CadQuery release, imprints an assembly in place. Every part keeps its name
and its place in the assembly, so you can pass the imprinted assembly straight
to cad_to_dagmc, take the material tags from the part names, and skip the BREP
file.

<!--pytest.mark.skipif(not hasattr(__import__("cadquery").Assembly, "imprint"), reason="needs a CadQuery with Assembly.imprint")-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

big = cq.Workplane("XY").box(10, 10, 10)
small = cq.Workplane("XY").transformed(offset=(0, 0, 7)).box(4, 4, 4)

assembly = cq.Assembly()
assembly.add(big, name="steel")
assembly.add(small, name="tungsten")

# Imprints in place: the parts keep their names and their order
assembly.imprint(glue="partial")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

# The assembly is already imprinted, so do not imprint it again
model.export_dagmc_h5m_file(filename="imprinted_in_memory.h5m", imprint=False)
```

An assembly with a single part has nothing to imprint, and `Assembly.imprint`
fails on it, so only imprint assemblies of two or more parts.

If two parts overlap, `Assembly.imprint` puts the region they share in both of
them. `add_cadquery_object()` finds that and raises a `ValueError` naming the
parts, even though exporting with `imprint=False` skips the overlap checks of
the export's own imprint; see [What exporting checks](overlaps.md#what-exporting-checks).

### Different Glue for Different Subassemblies

The [glue](#choosing-the-imprint-glue) is one setting for the whole imprint,
so a model whose contacts mostly coincide exactly still pays for `"partial"`
everywhere if a few contacts need it. Imprinting it yourself lets each
subassembly use the glue its own contacts need:

1. Imprint each subassembly with its own glue.
2. Add the imprinted subassemblies to one assembly.
3. Imprint that assembly once more, to connect the subassemblies to each other.

The last imprint uses the glue the contacts between the subassemblies need.
Where those faces coincide exactly, `"full"` is enough, even for a subassembly
imprinted with `"partial"`: its own faces were already split, so they now
coincide exactly too.

<!--pytest.mark.skipif(not hasattr(__import__("cadquery").Assembly, "imprint"), reason="needs a CadQuery with Assembly.imprint")-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc


def box(x, z=0, size=10):
    return cq.Workplane("XY").transformed(offset=(x, 0, z)).box(size, size, size)


# Two boxes whose touching faces coincide exactly, so full glue is enough
first = cq.Assembly(name="first")
first.add(box(0), name="armour")
first.add(box(10), name="structure")

# A small box on part of a big box's top face, which needs partial glue. The
# big box also touches "structure" in the first subassembly, face to face.
second = cq.Assembly(name="second")
second.add(box(20), name="blanket")
second.add(box(20, z=7, size=4), name="pipe")

# Imprint each subassembly BEFORE adding it: add() stores a copy, so imprinting
# the original afterwards does not change the combined assembly
first.imprint(glue="full")
second.imprint(glue="partial")

combined = cq.Assembly()
combined.add(first)
combined.add(second)

# Connect the subassemblies. Their contact coincides exactly, so full glue is
# enough here; use "partial" if a contact between them is only partial.
combined.imprint(glue="full")

model = CadToDagmc()
model.add_cadquery_object(combined, material_tags="assembly_names")
model.export_dagmc_h5m_file(filename="mixed_glue.h5m", imprint=False)
```

:::{warning}
`Assembly.add` stores a copy of a subassembly. Calling `imprint` on the
original after adding it changes the original only, and the combined assembly
is left unimprinted. Nothing reports this. Either imprint each subassembly
before adding it, as above, or imprint the copy held by the combined assembly,
`combined.objects["first"].imprint(glue="full")`. Skipping the last imprint
leaves the subassemblies unconnected, also without an error.
:::

The parts keep their names and their order through every imprint, so
`material_tags="assembly_names"` gives each volume its own part's name.

## Imprinting and Material Tag Order

Imprinting can change the order of the volumes. cad_to_dagmc reorders the
material tags to match, so each tag stays with its solid. Volume IDs given to
`set_size` or `unstructured_volumes` are the IDs after imprinting, which may not
follow the order you added the solids in, so give material tags there instead.

## See Also

- [Gmsh Backend](../meshing/gmsh_backend.md): meshing options
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md): sizing by material tag or volume ID
