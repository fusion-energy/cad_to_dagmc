# Manual Material Tags

Pass `material_tags` a list of strings, one tag per volume, in the order of the volumes.

## Basic Usage

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
    material_tags=["tungsten", "steel"],  # the sphere, then the box
)
model.export_dagmc_h5m_file()
```

The first tag goes to the first volume, the second to the second, and so on. A single volume still needs a list, such as `["steel"]`. When you call `add_cadquery_object` or `add_stp_file` more than once, each call takes the tags for its own volumes and the model keeps them in call order; see [Multiple Objects](../inputs/cadquery_objects.md#multiple-objects).

## Multiple Volumes with Same Material

Repeat a tag to give several volumes the same material:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# the text "DAGMC" is five solids, one per letter
text = cq.Workplane("XY").text("DAGMC", 10, 2)

model = CadToDagmc()
model.add_cadquery_object(text, material_tags=["letter"] * 5)
model.export_dagmc_h5m_file()
```

## With STEP Files

`add_stp_file` takes the same list. Pass it by keyword, because the second positional argument is `scale_factor`:

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_stp_file(filename="geometry.step", material_tags=["mat1", "mat2", "mat3"])
```

If the parts in the STEP file have useful names, [assembly names](assembly_names.md) can tag them by name instead.

## Determining Volume Count

The number of tags must equal the number of volumes. Otherwise `add_cadquery_object` and `add_stp_file` raise a `ValueError` that gives both counts, and a tag that is not a string raises a `TypeError`. CadQuery can count the solids before you write the list:

```python
import cadquery as cq

text = cq.Workplane("XY").text("HELLO", 10, 2)
print(len(text.val().Solids()))  # 5
```

For an assembly, count `assembly.toCompound().Solids()`. For a STEP file, count the solids of the imported shape. They come out in the order the tags are applied, so printing their centres shows which tag lands on which solid:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq

solids = cq.importers.importStep("geometry.step").val().Solids()
print(len(solids))
for index, solid in enumerate(solids):
    print(index, solid.Center())
```

## See Also

- [Tag Name Guidelines](index.md#tag-name-guidelines): reserved names and the length limit
- [Assembly Names](assembly_names.md): tags from part names, with no list to keep in order
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md): `set_size` gives a target mesh size per volume, keyed by material tag or volume ID (Gmsh backend only)
