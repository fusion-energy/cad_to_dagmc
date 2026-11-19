# Implicit Complement

The implicit complement is the space that no volume occupies: the gaps between
volumes and the space around them, out to the boundary of the model. With no
tag, DAGMC treats it as vacuum, so particles cross it without interacting and
none are lost. If that space holds air, water, helium or another material, name
the material with `implicit_complement_material_tag`.

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Two boxes with a gap between them
box1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
box2 = cq.Workplane("XY").moveTo(20, 0).box(10.0, 10.0, 5.0)

assembly = cq.Assembly()
assembly.add(box1)
assembly.add(box2)

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1", "mat2"])

model.export_dagmc_h5m_file(implicit_complement_material_tag="air")
```

The tag is stored as a group named `mat:air_comp`. DAGMC reads the `_comp`
suffix as marking the implicit complement material, so OpenMC fills the
implicit complement with the material named `air`.

Keep the tag to 22 characters or fewer. Each group name in the h5m file gets 32
bytes, and `mat:`, `_comp` and the null byte that ends the name take 10 of
them. cad_to_dagmc warns about a longer tag. With 23 characters there is no
room for the null byte, so DAGMC can misread the name and then not find the
material. A longer tag is cut to fit and loses its `_comp` suffix, and DAGMC
stops while loading the file with "More than one material for volume ...". The
other naming rules are in [Tag Name Guidelines](../material_tagging/index.md#tag-name-guidelines).

## Using in OpenMC

Define a material with the same name as the tag:

<!--pytest-codeblocks:skip-->
```python
import openmc

# Fills the implicit complement
air = openmc.Material(name="air")
air.add_element("N", 0.78)
air.add_element("O", 0.22)
air.set_density("g/cm3", 0.001225)

# mat1 and mat2, named after the volume tags, are defined as usual
materials = openmc.Materials([air, mat1, mat2])

universe = openmc.DAGMCUniverse("dagmc.h5m").bounded_universe()
geometry = openmc.Geometry(universe)
```

## With Gmsh Files

`export_gmsh_file_to_dagmc_h5m_file` and `export_gmsh_object_to_dagmc_h5m_file`
take the same argument:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m",
    material_tags=["mat1", "mat2"],
    implicit_complement_material_tag="air",
)
```

## See Also

- [DAGMC h5m Files](../outputs/dagmc_h5m.md): the other export options
- [Gmsh Files](../inputs/gmsh_files.md): converting a Gmsh mesh to DAGMC
