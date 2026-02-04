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
sphere = cq.Workplane("XY").moveTo(100, 0).sphere(5)

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

# Create shapes with splines
spline_points = [
    (2.75, 1.5),
    (2.5, 1.75),
    (2.0, 1.5),
    (1.5, 1.0),
    (1.0, 1.25),
    (0.5, 1.0),
    (0, 1.0),
]

s = cq.Workplane("XY")
r = s.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
shape1 = r.extrude(-1)

s2 = cq.Workplane("XY")
r2 = s2.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
shape2 = r2.extrude(1)

# Create a compound from both shapes
compound = cq.Compound.makeCompound([shape1.val(), shape2.val()])

# Add compound - needs one tag per solid in the compound
model = CadToDagmc()
model.add_cadquery_object(cadquery_object=compound, material_tags=["mat1", "mat2"])
model.export_dagmc_h5m_file(max_mesh_size=0.2, min_mesh_size=0.1)
```

## Complex Curved Geometry

CadQuery supports complex parametric curves. Here's an example with a twisted gear profile:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc
from math import sin, cos, pi, floor

def hypocycloid(t, r1, r2):
    return (
        (r1 - r2) * cos(t) + r2 * cos(r1 / r2 * t - t),
        (r1 - r2) * sin(t) + r2 * sin(-(r1 / r2 * t - t)),
    )

def epicycloid(t, r1, r2):
    return (
        (r1 + r2) * cos(t) - r2 * cos(r1 / r2 * t + t),
        (r1 + r2) * sin(t) - r2 * sin(r1 / r2 * t + t),
    )

def gear(t, r1=4, r2=1):
    if (-1) ** (1 + floor(t / 2 / pi * (r1 / r2))) < 0:
        return epicycloid(t, r1, r2)
    else:
        return hypocycloid(t, r1, r2)

# Create gear profile with twist extrude
result = (
    cq.Workplane("XY")
    .parametricCurve(lambda t: gear(t * 2 * pi, 6, 1))
    .twistExtrude(15, 90)
    .faces(">Z")
    .workplane()
    .circle(2)
    .cutThruAll()
)

model = CadToDagmc()
model.add_cadquery_object(result, material_tags=["gear_material"])
model.export_dagmc_h5m_file(max_mesh_size=1, min_mesh_size=0.1)
```

## Text Geometry

CadQuery can create text, which results in multiple volumes (one per character):

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create 3D text - each letter is a separate volume
text = cq.Workplane("XY").text("DAGMC", 10, 2)

# Count the volumes
num_volumes = len(text.val().Solids())
print(f"Text has {num_volumes} volumes")

# Each volume needs a material tag
model = CadToDagmc()
model.add_cadquery_object(text, material_tags=["letter"] * num_volumes)
model.export_dagmc_h5m_file()
```

## API Reference

### `add_cadquery_object()`

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
