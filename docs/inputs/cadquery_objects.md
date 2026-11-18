# CadQuery Objects

Geometry built in Python with CadQuery is added to the model with `add_cadquery_object()`.

## Supported Object Types

- `cq.Workplane`. Only the first object on its stack (`workplane.val()`) is used. That is normally the whole result, even when it holds several solids, as `text()` does. After `combine=False` each solid is its own object, so only the first would be added.
- `cq.Solid` or `cq.Compound`. Each solid becomes one volume.
- `cq.Assembly`. Its tags can also come from its part names or `cq.Material` objects; see [CadQuery Assemblies](cadquery_assemblies.md).

## Basic Example

Create a simple shape and convert it:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane("XY").sphere(5)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=sphere, material_tags=["mat1"])
model.export_dagmc_h5m_file()
```

## Multiple Objects

Call `add_cadquery_object()` once per object, each with its own tags. Volumes, and their material tags, keep the order they were added in, and `add_stp_file()` calls can be mixed in.

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

box = cq.Workplane("XY").moveTo(2, 0).box(2, 2, 2)
small_box = cq.Workplane("XY").box(2, 1, 1)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=box, material_tags=["mat1"])
model.add_cadquery_object(cadquery_object=small_box, material_tags=["mat2"])
model.export_dagmc_h5m_file()
```

## Using Compounds

A Compound groups several solids into one object, and takes one tag per solid:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

box = cq.Workplane("XY").moveTo(2, 0).box(2, 2, 2)
small_box = cq.Workplane("XY").box(2, 1, 1)

compound = cq.Compound.makeCompound([box.val(), small_box.val()])

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=compound, material_tags=["mat1", "mat2"])
model.export_dagmc_h5m_file()
```

## API Reference

### `add_cadquery_object()`

| Parameter | Type | Description |
|-----------|------|-------------|
| `cadquery_object` | Workplane, Solid, Compound or Assembly | The CadQuery geometry to add |
| `material_tags` | list[str] or str | A list with one tag per volume, or `"assembly_names"` / `"assembly_materials"` for an assembly; see [Material Tagging](../material_tagging/index.md) |
| `scale_factor` | float | Scales the geometry as it is added (default 1.0); see [Geometry Scaling](../advanced/geometry_scaling.md) |

It returns the number of volumes added. Exact signatures are on the [API Reference](../api.md) page.

## See Also

- [CadQuery Assemblies](cadquery_assemblies.md): tags from part names or `cq.Material` objects
- [Manual Tags](../material_tagging/manual_tags.md): lists of material tags in detail
- [CadQuery Documentation](https://cadquery.readthedocs.io/): building the geometry
