# Assembly Materials as Tags

CadQuery 2.6.1+ supports `cq.Material` objects for assembly parts. Use these as material tags for cleaner separation between part identity (name) and material assignment.

## Basic Usage

Assign materials to assembly parts, then use `material_tags="assembly_materials"`:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere, name="large_sphere", material=cq.Material("tungsten"))
assembly.add(small_sphere, name="small_sphere", material=cq.Material("steel"))

model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_materials"  # Use Material objects as tags
)
model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)
```

This creates volumes tagged with `mat:tungsten` and `mat:steel`.

## When to Use Assembly Materials

| Use Case | Recommendation |
|----------|----------------|
| Part names describe geometry | Use `assembly_materials` |
| Part names describe materials | Use `assembly_names` |
| Multiple parts, same material | Use `assembly_materials` |
| Need CadQuery < 2.6.1 | Use `assembly_names` or manual |

## Example: Names vs Materials

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()

# Name describes geometry, material describes composition
assembly.add(
    cq.Workplane().sphere(5),
    name="inner_shield",           # Geometric description
    material=cq.Material("tungsten")  # Material composition
)
assembly.add(
    cq.Workplane().sphere(10).cut(cq.Workplane().sphere(5)),
    name="outer_shield",           # Geometric description
    material=cq.Material("tungsten")  # Same material!
)
assembly.add(
    cq.Workplane().box(30, 30, 30),
    name="coolant_channel",
    material=cq.Material("water")
)

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_materials")

print(model.material_tags)
# Output: ['tungsten', 'tungsten', 'water']
```

## Multiple Parts, Same Material

The material tag is reused for parts with the same material:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()

# Multiple fuel pins, all tungsten
for i in range(5):
    assembly.add(
        cq.Workplane().moveTo(i * 3, 0).cylinder(10, 0.5),
        name=f"fuel_pin_{i}",
        material=cq.Material("tungsten")  # All share same material
    )

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_materials")
# All 5 volumes tagged with "tungsten"
```

## Requirements and Errors

:::{warning}
**CadQuery version**: This feature requires CadQuery > 2.6.1.

**All parts need materials**: Every part must have a material assigned, or you'll get an error:

```python
assembly.add(sphere, name="sphere")  # No material!
model.add_cadquery_object(assembly, material_tags="assembly_materials")
# ValueError: Part 'sphere' has no material assigned
```
:::

Check your CadQuery version:

```python
import cadquery
print(cadquery.__version__)
```

## Comparison with Assembly Names

| Feature | `assembly_names` | `assembly_materials` |
|---------|------------------|---------------------|
| Tag source | `name="..."` | `material=cq.Material("...")` |
| CadQuery version | Any | > 2.6.1 |
| Unnamed parts | Gets UUID | Error |
| Same tag for multiple parts | Must use same name | Use same Material |

## See Also

- [Assembly Names](assembly_names.md) - Alternative: use part names as tags
- [CadQuery Assemblies](../inputs/cadquery_assemblies.md) - Assembly input guide
- [CadQuery Material Documentation](https://cadquery.readthedocs.io/) - Official CadQuery docs
