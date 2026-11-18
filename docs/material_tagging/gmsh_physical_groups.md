# Gmsh Physical Groups

When a Gmsh mesh is converted without `material_tags`, cad_to_dagmc takes the material tags from the names of its 3D physical groups. Both `export_gmsh_file_to_dagmc_h5m_file` (a `.msh` file) and `export_gmsh_object_to_dagmc_h5m_file` (the model in the current gmsh session) do this.

## How It Works

The names of the 3D physical groups are read in order of group tag and paired with the volumes in order of volume tag. Which volumes a group contains is never checked. So make exactly one 3D group per volume, and create the groups in volume order or give them tags in that order.

A group that holds two volumes leaves fewer names than volumes, and the conversion raises a `ValueError` such as "Number of volumes 3 is not equal to number of material tags 2". Groups created in a different order from the volumes swap the tags without any error. Groups of other dimensions are ignored. Group names become tags unchanged and must follow the [tag name guidelines](index.md#tag-name-guidelines).

## Creating Physical Groups

A sphere inside a box, with one group per volume:

```python
import gmsh

gmsh.initialize()

# fragment keeps both volumes and gives them one shared surface
gmsh.model.occ.addSphere(0, 0, 0, 1, tag=1)
gmsh.model.occ.addBox(-2, -2, -2, 4, 4, 4, tag=2)
gmsh.model.occ.fragment([(3, 2)], [(3, 1)])
gmsh.model.occ.synchronize()

# one 3D group per volume, in volume order
gmsh.model.addPhysicalGroup(3, [1], name="tungsten")
gmsh.model.addPhysicalGroup(3, [2], name="water")

gmsh.model.mesh.generate(2)

# the surface triangles belong to no physical group, so save them explicitly
gmsh.option.setNumber("Mesh.SaveAll", 1)
gmsh.write("mesh_with_groups.msh")
gmsh.finalize()
```

Once a model has physical groups, Gmsh saves only the elements that belong to one. Without `Mesh.SaveAll`, the file above would hold no surface triangles and the conversion would fail with an `IndexError`.

## Using assembly-mesh-plugin

The [assembly-mesh-plugin](https://github.com/CadQuery/assembly-mesh-plugin) adds `getTaggedGmsh()` to CadQuery assemblies. It initialises gmsh and loads the assembly, with a 3D group for each solid named after its part:

```python
import cadquery as cq
import cad_to_dagmc
import gmsh
import assembly_mesh_plugin  # adds getTaggedGmsh to cq.Assembly

box1 = cq.Workplane("XY").box(50, 50, 50)
box2 = cq.Workplane("XY").moveTo(0, 50).box(50, 50, 100)

assembly = cq.Assembly()
assembly.add(box1, name="first_material")
assembly.add(box2, name="second_material")

assembly.getTaggedGmsh()

gmsh.option.setNumber("Mesh.MeshSizeMax", 4.2)
gmsh.model.mesh.generate(2)

cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc.h5m")

gmsh.finalize()
```

The plugin also adds a 3D group named `mat:<material>` for every part that has a `cq.Material`. That gives more names than volumes: with materials on both parts above, the conversion raises "Number of volumes 2 is not equal to number of material tags 4". Leave materials off the parts, or pass `material_tags`.

Each part goes into gmsh separately, so parts that touch, like the two boxes above, keep separate copies of the face where they meet instead of sharing one surface; see [Imprinting](../advanced/imprinting.md) for why that matters. `CadToDagmc` with [assembly names](assembly_names.md) gives the same tags and imprints the parts when it exports.

## Converting a Mesh File

With the groups in place, `material_tags` can be left out:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh_with_groups.msh",
    dagmc_filename="dagmc.h5m",
)
```

The conversion prints the names it found, in the order it applies them.

## Checking Physical Groups

To see which volumes each group holds before converting:

<!--pytest-codeblocks:skip-->
```python
import gmsh

gmsh.initialize()
gmsh.open("mesh_with_groups.msh")

print("volumes:", [tag for _, tag in gmsh.model.getEntities(3)])
for dim, tag in gmsh.model.getPhysicalGroups(3):
    name = gmsh.model.getPhysicalName(dim, tag)
    volumes = [int(v) for v in gmsh.model.getEntitiesForPhysicalGroup(dim, tag)]
    print(f"group {tag}: {name}, volumes {volumes}")

gmsh.finalize()
```

The tags are right when the first group holds only the first volume, the second group only the second, and so on.

## Overriding Physical Groups

`material_tags`, when given, is used instead of the groups, one tag per volume in volume order. This also fixes groups that are out of order or hold several volumes:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh_with_groups.msh",
    dagmc_filename="dagmc.h5m",
    material_tags=["lead", "water"],
)
```

## Materials in OpenMC

Name the OpenMC materials after the groups:

<!--pytest-codeblocks:skip-->
```python
import openmc

tungsten = openmc.Material(name="tungsten")
tungsten.add_element("W", 1.0)
tungsten.set_density("g/cm3", 19.3)

water = openmc.Material(name="water")
water.add_element("H", 2.0)
water.add_element("O", 1.0)
water.set_density("g/cm3", 1.0)
```

The rest of the model is set up as in [Using in OpenMC](../outputs/dagmc_h5m.md#using-in-openmc).

## See Also

- [Gmsh Files](../inputs/gmsh_files.md): converting a Gmsh mesh, with or without physical groups
- [Gmsh physical groups](https://gmsh.info/doc/texinfo/gmsh.html#Physical-groups): the Gmsh documentation
