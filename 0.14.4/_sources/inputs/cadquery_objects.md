# CadQuery Objects

CadQuery objects are the most flexible input option. Create geometry programmatically in Python and convert directly to DAGMC format.

## Supported Object Types

- **Workplane results** (Solid) - Single solid shapes
- **Compound** - Multiple solids grouped together
- **Assembly** - See [CadQuery Assemblies](cadquery_assemblies.md) for assembly-specific features

## Basic Example

Create a simple shape and convert it:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create a sphere
sphere = cq.Workplane("XY").sphere(5)

# Convert to DAGMC
model = CadToDagmc()
model.add_cadquery_object(cadquery_object=sphere, material_tags=["mat1"])
model.export_dagmc_h5m_file()
```

## Multiple Objects

Add multiple CadQuery objects separately:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create two separate shapes
box = cq.Workplane("XY").moveTo(2, 0).box(2, 2, 2)
cylinder = cq.Workplane("XY").box(2, 1, 1)

# Add each with its own material tag
model = CadToDagmc()
model.add_cadquery_object(cadquery_object=box, material_tags=["mat1"])
model.add_cadquery_object(cadquery_object=cylinder, material_tags=["mat2"])
model.export_dagmc_h5m_file()
```

## Using Compounds

A Compound groups multiple solids into a single object:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

box = cq.Workplane("XY").moveTo(2, 0).box(2, 2, 2)
cylinder = cq.Workplane("XY").box(2, 1, 1)

# Create a compound from both shapes
compound = cq.Compound.makeCompound([box.val(), cylinder.val()])

# Add compound - needs one tag per solid in the compound
model = CadToDagmc()
model.add_cadquery_object(cadquery_object=compound, material_tags=["mat1", "mat2"])
model.export_dagmc_h5m_file(max_mesh_size=0.2, min_mesh_size=0.1)
```

## Using Assemblies

Assemblies allow you to name parts and use those names as material tags:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create shapes
sphere = cq.Workplane().sphere(5)
box = cq.Workplane().moveTo(15, 0).box(5, 5, 5)

# Create assembly with named parts
assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")
assembly.add(box, name="steel")

# Use assembly names as material tags
model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_names"  # Names become material tags
)
model.export_dagmc_h5m_file()
```

See [CadQuery Assemblies](cadquery_assemblies.md) for more assembly features including nested assemblies and using `cq.Material` objects.

## API Reference

### `add_cadquery_object()`

<!--pytest-codeblocks:skip-->
```python
model.add_cadquery_object(
    cadquery_object,      # CadQuery Solid, Compound, or Assembly
    material_tags,        # List of tags, or "assembly_names"/"assembly_materials"
    scale_factor=1.0,     # Optional geometry scaling
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `cadquery_object` | Solid, Compound, Assembly | The CadQuery geometry to add |
| `material_tags` | list[str] or str | Material tag(s) for each volume |
| `scale_factor` | float | Scale geometry by this factor (default: 1.0) |

**Material tags options:**

- `["mat1", "mat2", ...]` - Explicit list (one per volume)
- `"assembly_names"` - Use assembly part names as tags
- `"assembly_materials"` - Use `cq.Material` objects as tags (CadQuery > 2.6.1)

## See Also

- [CadQuery Assemblies](cadquery_assemblies.md) - For multi-part assemblies with automatic tagging
- [Manual Tags](../material_tagging/manual_tags.md) - Detailed material tagging guide
- [CadQuery Documentation](https://cadquery.readthedocs.io/) - Official CadQuery docs
