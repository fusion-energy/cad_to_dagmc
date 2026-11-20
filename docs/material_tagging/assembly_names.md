# Assembly Names as Material Tags

With `material_tags="assembly_names"`, each part of a CadQuery assembly is tagged with its name, so there is no list to keep in the order of the volumes. `add_stp_file` takes it too and reads the part names stored in a STEP file; [Tags from Named STEP Parts](../inputs/step_files.md#tags-from-named-step-parts) has an example and a warning about part names that end in `_part`.

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")
assembly.add(small_sphere, name="steel")

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_names")
model.export_dagmc_h5m_file()
```

This writes volumes tagged `mat:tungsten` and `mat:steel`. Because the tag travels with the part, adding or removing parts cannot shift the other tags, and the code shows what each part is made of. Only the name is read; a part's `color` or `material` does not change its tag. Names become tags unchanged and must follow the [tag name guidelines](index.md#tag-name-guidelines).

## Unnamed Parts

CadQuery names a part added without `name` with a UUID:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)

assembly = cq.Assembly()
assembly.add(sphere, name="sphere")
# cut the sphere out of the box so the two solids do not overlap
assembly.add(cq.Workplane().box(10, 10, 10).cut(sphere))  # no name

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

print(model.material_tags)
# ['sphere', '<a new UUID>']
```

The UUID changes every time the assembly is built. At 36 characters it is also over the length limit, so cad_to_dagmc warns and the h5m file keeps only its first 28 characters. Name every part.

## Repeated Names and Nested Assemblies

Parts added to the same assembly need different names. CadQuery rejects a repeat with a `ValueError` that starts "Unique name is required". To give several solids one tag, put them in one part (every solid in a part gets the part's name) or tag them with [assembly materials](assembly_materials.md).

In a nested assembly, each part is tagged with its own name and the sub-assembly names are not used. Parts in different sub-assemblies can therefore share a name, and a tag:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

left = cq.Assembly(name="left")
left.add(cq.Workplane().moveTo(-5, 0).box(1, 1, 1), name="pin")

right = cq.Assembly(name="right")
right.add(cq.Workplane().moveTo(5, 0).box(1, 1, 1), name="pin")

assembly = cq.Assembly()
assembly.add(left)
assembly.add(right)

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")
print(model.material_tags)  # ['pin', 'pin']
```

## See Also

- [Assembly Materials](assembly_materials.md): tags from `cq.Material`, for parts that share a material
- [CadQuery Assemblies](../inputs/cadquery_assemblies.md): adding assemblies to a model
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md): `set_size` gives a target mesh size per volume, keyed by material tag or volume ID (Gmsh backend only)
