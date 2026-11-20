# CadQuery Assemblies

A `cq.Assembly` is added with `add_cadquery_object()`, like any other CadQuery object, and each solid in it becomes one volume. Its material tags can be a list, or come from the parts themselves.

## Basic Assembly

A list gives one tag per solid, in the order the parts were added to the assembly:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane().sphere(5)
small_sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere)
assembly.add(small_sphere)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1", "mat2"])
model.export_dagmc_h5m_file()
```

## Tagging Options

Instead of a list, `material_tags="assembly_names"` takes each tag from the part's `name`, and `material_tags="assembly_materials"` from the name of its `cq.Material`. [Assembly Names](../material_tagging/assembly_names.md) and [Assembly Materials](../material_tagging/assembly_materials.md) cover both, and [Manual Tags](../material_tagging/manual_tags.md) covers lists.

However the volumes are tagged, `set_size` can use the tags, or volume IDs, to give volumes their own target mesh size. It works on the Gmsh backend only; see [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md).

## Nested Assemblies

An assembly can contain other assemblies:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

pin_1 = cq.Workplane().cylinder(10, 1)
pin_2 = cq.Workplane().moveTo(3, 0).cylinder(10, 1)

fuel_assembly = cq.Assembly()
fuel_assembly.add(pin_1, name="fuel_pin_1")
fuel_assembly.add(pin_2, name="fuel_pin_2")

# Cut the pins out of the coolant so the solids do not overlap
coolant = cq.Workplane().box(20, 20, 12).cut(pin_1).cut(pin_2)

main_assembly = cq.Assembly()
main_assembly.add(fuel_assembly, name="fuel")
main_assembly.add(coolant, name="coolant")

model = CadToDagmc()
model.add_cadquery_object(main_assembly, material_tags="assembly_names")
print(model.material_tags)  # ['fuel_pin_1', 'fuel_pin_2', 'coolant']
model.export_dagmc_h5m_file()
```

The tags come from the leaf parts. The sub-assembly name `fuel` is not used.

## See Also

- [Assembly Names](../material_tagging/assembly_names.md): naming rules, and the tags unnamed parts get
- [Assembly Materials](../material_tagging/assembly_materials.md): tagging with `cq.Material`, and parts that share a material
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md): a mesh size per volume on the Gmsh backend
