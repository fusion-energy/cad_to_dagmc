# Output Formats

cad_to_dagmc can create three types of output file, and can write a conformal
surface and volume mesh pair in a single call.

## Output Types

| Output | Method | Mesh and file | Use |
|--------|--------|---------------|-----|
| [DAGMC h5m Files](dagmc_h5m.md) | `export_dagmc_h5m_file()` | Surface mesh of triangles, `.h5m` | Geometry for particle transport |
| [Unstructured Mesh VTK Files](unstructured_vtk.md) | `export_unstructured_mesh_file()` | Volume mesh of tetrahedra, `.vtk` | Unstructured mesh tallies in OpenMC |
| [Conformal Meshes](conformal_meshes.md) | `export_dagmc_h5m_file()` | Both of the above, sharing their surfaces | Transport and mesh tallies on matching meshes |
| [Gmsh Mesh Files](gmsh_mesh.md) | `export_gmsh_mesh_file()` | Gmsh surface or volume mesh, `.msh` | Inspecting the mesh, converting to h5m later |

## Basic Export Pattern

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten"])

# Surface mesh, from the default cad-to-dagmc-mesher backend
model.export_dagmc_h5m_file(filename="dagmc.h5m")

# Volume mesh. Without target_edge_length this runs on Gmsh, with
# min_mesh_size=1 and max_mesh_size=5
model.export_unstructured_mesh_file(filename="umesh.vtk")

# Gmsh's own format, a surface mesh unless dimensions=3
model.export_gmsh_mesh_file(filename="mesh.msh")
```

The meshing arguments you pass decide the backend of the first two calls; see
[How the Backend Is Chosen](../meshing/index.md#how-the-backend-is-chosen).
`export_gmsh_mesh_file()` always uses Gmsh.

## Choosing an Output Format

Every DAGMC simulation needs the h5m file, whichever DAGMC-enabled code runs it
(OpenMC, MCNP, FLUKA). Add a VTK volume mesh when you tally on an unstructured
mesh in OpenMC, or need a volume mesh for another tool. Separate export calls
each mesh the geometry, so the h5m and VTK files above are not conformal. When
the tally mesh has to match the geometry, write both from one call as
[conformal meshes](conformal_meshes.md).

A DAGMC simulation does not need the Gmsh mesh file. Write one to look at a mesh
in the Gmsh GUI, or to mesh once and convert to h5m later.
