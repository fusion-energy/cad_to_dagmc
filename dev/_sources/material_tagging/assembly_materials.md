# Assembly Materials as Tags

With `material_tags="assembly_materials"`, each part of a CadQuery assembly is tagged with the name of its `cq.Material`. Use it when the part names describe the geometry rather than the material, and whenever sibling parts share a material. CadQuery rejects a repeated name among the parts of one assembly, so [assembly names](assembly_names.md) cannot give them one tag.

`add_stp_file` takes `material_tags="assembly_materials"` too, for STEP files that store materials; [Tags from Named STEP Parts](../inputs/step_files.md#tags-from-named-step-parts) has a warning about part names that end in `_part`.

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere, name="large_sphere", material=cq.Material("tungsten"))
assembly.add(small_sphere, name="small_sphere", material=cq.Material("steel"))

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_materials")
model.export_dagmc_h5m_file()
```

This writes volumes tagged `mat:tungsten` and `mat:steel`. CadQuery also accepts a plain string, `material="tungsten"`.

Every part needs a material. If one has none, adding the assembly raises a `ValueError` that starts "Not all parts in the assembly have materials assigned". This is stricter than `assembly_names`, which gives an unnamed part a UUID tag.

## Several Parts, One Material

Parts with the same material share a tag, while their names stay distinct:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

inner = cq.Workplane().sphere(5)
outer = cq.Workplane().sphere(10).cut(inner)
coolant = cq.Workplane().box(30, 30, 30).cut(cq.Workplane().sphere(10))

assembly = cq.Assembly()
assembly.add(inner, name="inner_shield", material=cq.Material("tungsten"))
assembly.add(outer, name="outer_shield", material=cq.Material("tungsten"))
assembly.add(coolant, name="coolant", material=cq.Material("water"))

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_materials")
print(model.material_tags)  # ['tungsten', 'tungsten', 'water']
```

## See Also

- [CadQuery Assemblies](../inputs/cadquery_assemblies.md): adding assemblies to a model
- [CadQuery documentation](https://cadquery.readthedocs.io/): `cq.Assembly` and `cq.Material`
