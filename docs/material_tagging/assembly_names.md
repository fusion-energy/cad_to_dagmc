# Assembly Names as Material Tags

Use CadQuery assembly part names automatically as material tags. This avoids manual tag ordering.

## Basic Usage

Name your assembly parts, then use `material_tags="assembly_names"`:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")      # Name becomes material tag
assembly.add(small_sphere, name="steel")   # Name becomes material tag

model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_names"  # Use names as tags
)
model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)
```

This creates volumes tagged with `mat:tungsten` and `mat:steel`.

## Why Use Assembly Names?

| Advantage | Explanation |
|-----------|-------------|
| No ordering issues | Tags come from the part, not position in a list |
| Self-documenting | Code shows what each part is |
| Works with set_size | Tag names can reference mesh sizing |
| Refactoring safe | Adding/removing parts won't break tag assignment |

## Using Names with Mesh Sizing

Assembly names work seamlessly with the `set_size` parameter:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
default_box = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(coarse_box, name="coarse")
assembly.add(fine_box, name="fine")
assembly.add(default_box, name="global")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

# Check available material tags
print("Material tags:", model.material_tags)
# Output: Material tags: ['coarse', 'fine', 'global']

model.export_dagmc_h5m_file(
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,  # Reference by name
        "fine": 0.1,
        # "global" uses default min/max
    },
)
```

## Unnamed Parts

Parts without explicit names receive auto-generated UUIDs:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane().sphere(5), name="named_part")
assembly.add(cq.Workplane().box(10, 10, 10))  # No name!

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

print(model.material_tags)
# Output: ['named_part', 'a1b2c3d4-e5f6-...']  # UUID for unnamed part
```

:::{warning}
Always name your assembly parts to ensure meaningful, predictable material tags. UUID tags are hard to reference in simulations.
:::

## Naming Conventions

Recommended naming practices:

<!--pytest-codeblocks:skip-->
```python
# Good names - descriptive, match OpenMC materials
assembly.add(inner_wall, name="tungsten")
assembly.add(cooling_channel, name="water")
assembly.add(outer_shell, name="steel")

# Avoid - too generic
assembly.add(part1, name="part1")
assembly.add(part2, name="part2")

# Avoid - too long (may be truncated)
assembly.add(component, name="plasma_facing_component_tungsten_armor")
```

## Using Colors for Visualization

You can add colors without affecting material tags:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(
    cq.Workplane().box(1, 1, 2),
    name="coarse",
    color=cq.Color(0, 0, 1),  # Blue - for visualization only
)
assembly.add(
    cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5),
    name="fine",
    color=cq.Color(0, 1, 0),  # Green
)

# Material tags are still "coarse" and "fine"
model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")
```

## See Also

- [Assembly Materials](assembly_materials.md) - Alternative: use cq.Material objects
- [CadQuery Assemblies](../inputs/cadquery_assemblies.md) - Assembly input guide
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Using tag names for mesh control
