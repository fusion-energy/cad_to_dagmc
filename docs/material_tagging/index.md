# Material Tagging

Material tags identify each volume in the DAGMC geometry. They connect your CAD geometry to materials in your neutronics simulation.

## Tagging Methods

| Method | Description | Best For |
|--------|-------------|----------|
| [Manual Tags](manual_tags.md) | Explicit list of tag strings | Simple models, STEP files |
| [Assembly Names](assembly_names.md) | Use CadQuery assembly part names | CadQuery assemblies |
| [Assembly Materials](assembly_materials.md) | Use `cq.Material` objects | CadQuery 2.6.1+ |
| [GMSH Physical Groups](gmsh_physical_groups.md) | Extract from GMSH mesh | Pre-existing meshes |

## Quick Comparison

| Feature | Manual Tags | Assembly Names | Assembly Materials | GMSH Groups |
|---------|-------------|----------------|-------------------|-------------|
| Requires ordering | Yes | No | No | No |
| Auto from geometry | No | Yes | Yes | Yes |
| Works with STEP | Yes | No | No | No |
| CadQuery version | Any | Any | > 2.6.1 | Any |

## How Tags Are Stored

Material tags are stored in the h5m file with a `mat:` prefix:

- `"tungsten"` becomes `"mat:tungsten"` in the h5m file
- `"steel"` becomes `"mat:steel"` in the h5m file

When using in OpenMC, reference materials without the prefix:

<!--pytest-codeblocks:skip-->
```python
import openmc

# Material name matches the tag (without "mat:" prefix)
tungsten = openmc.Material(name="tungsten")
tungsten.add_element("W", 1.0)
tungsten.set_density("g/cm3", 19.3)
```

## Tag Name Guidelines

:::{warning}
DAGMC truncates material tag names longer than 28 characters. Keep your tags concise.
:::

Recommended practices:
- Use descriptive but short names: `"fuel"`, `"coolant"`, `"shield"`
- Avoid special characters
- Use lowercase for consistency
- Match names to your OpenMC material definitions
