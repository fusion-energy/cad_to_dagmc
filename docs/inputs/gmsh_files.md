# Gmsh Files

An existing Gmsh mesh, either a `.msh` file or the model in the current gmsh session, converts straight to a DAGMC h5m file. Its surface triangles are written as they are, without remeshing. Use this when you already have a mesh, or want to run Gmsh yourself.

## From Gmsh File with Manual Tags

This example writes a Gmsh mesh file from a STEP file, then converts it:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc
import cad_to_dagmc

# First, create a Gmsh mesh file (for this example)
result1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cq.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = cq.Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.export("two_connected_cubes.step")

geometry = CadToDagmc()
geometry.add_stp_file("two_connected_cubes.step")
geometry.export_gmsh_mesh_file(filename="example_gmsh_mesh.msh")

# Now convert the Gmsh mesh file to DAGMC
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="example_gmsh_mesh.msh",
    material_tags=["mat1", "mat2"],
    dagmc_filename="dagmc.h5m",
)
```

The STEP file is added without material tags, which is allowed because `export_gmsh_mesh_file()` does not need them. The `.msh` file it writes has no physical groups either, so the tags are given at conversion, one per volume in the order of the volumes in the mesh. Without them the conversion raises `ValueError: Number of volumes 2 is not equal to number of material tags 0`.

## From Gmsh File with Physical Groups

When `material_tags` is not given, the tags are the names of the mesh's 3D physical groups, paired with the volumes by position. Make exactly one 3D group per volume, in volume order; [Gmsh Physical Groups](../material_tagging/gmsh_physical_groups.md) has the rules and shows how to create the groups. In OpenMC, name each material after its group, as in [Using in OpenMC](../outputs/dagmc_h5m.md#using-in-openmc).

## From Gmsh Object in Memory

`export_gmsh_object_to_dagmc_h5m_file()` converts the model in the current gmsh session. Building and meshing the model with the gmsh API yourself gives access to every Gmsh option, including those the cad_to_dagmc exports do not set. Initialise gmsh and generate the surface mesh before the call. The function leaves the session open, so finalise gmsh afterwards.

```python
import gmsh
import cad_to_dagmc

gmsh.initialize()
gmsh.model.occ.addSphere(0, 0, 0, 5)           # volume 1
gmsh.model.occ.addBox(10, -5, -5, 10, 10, 10)  # volume 2
gmsh.model.occ.synchronize()

# Any Gmsh option can be set before meshing, here sizing from curvature
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 20)
gmsh.model.mesh.generate(2)

cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(
    filename="dagmc.h5m",
    material_tags=["mat1", "mat2"],
)

gmsh.finalize()
```

As with a file, the tags come from `material_tags` or, when it is not given, from the names of the 3D physical groups. Solids that touch should share the face between them, which `gmsh.model.occ.fragment` does. Fragmenting can drop physical groups, so add them afterwards.

The [assembly-mesh-plugin](https://github.com/CadQuery/assembly-mesh-plugin) loads a CadQuery assembly into the session with a physical group per part, but does not merge the faces of parts that touch; see [Gmsh Physical Groups](../material_tagging/gmsh_physical_groups.md).

## API Reference

`export_gmsh_file_to_dagmc_h5m_file()` (file) starts gmsh and finalises it when done, which also closes any gmsh session you already had open. `export_gmsh_object_to_dagmc_h5m_file()` (object) uses the caller's session and leaves it open. Both return the name of the h5m file, and raise `ValueError` when the number of tags differs from the number of volumes.

| Parameter | Function | Description |
|-----------|----------|-------------|
| `gmsh_filename` | file | The `.msh` file to read |
| `material_tags` | both | One tag per volume, in volume order. If not given, the names of the 3D physical groups are used |
| `implicit_complement_material_tag` | both | Material for the implicit complement, the space between and around the volumes (default None, vacuum); see [Implicit Complement](../advanced/implicit_complement.md) |
| `dagmc_filename` | file | The h5m file to write (default `"dagmc.h5m"`) |
| `filename` | object | The h5m file to write (default `"dagmc.h5m"`) |
| `h5m_backend` | both | `"h5py"` (default) or `"pymoab"`; see [h5m Backends](../advanced/h5m_backends.md) |

In both functions `material_tags` comes before the output file name, so pass the file name by keyword. Exact signatures are on the [API Reference](../api.md) page.

## See Also

- [Gmsh Physical Groups](../material_tagging/gmsh_physical_groups.md): tagging volumes with physical groups
- [Gmsh Backend](../meshing/gmsh_backend.md): meshing CAD with Gmsh from cad_to_dagmc
- [Gmsh Documentation](https://gmsh.info/doc/texinfo/gmsh.html): the Gmsh manual
