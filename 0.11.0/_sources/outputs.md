# Output Formats

cad_to_dagmc can create three types of output files.

## DAGMC H5M Files (Surface Mesh)

The primary output format. Creates triangular surface meshes for use with DAGMC-enabled
transport codes (OpenMC, MCNP, FLUKA, etc.).

```python
import cadquery as cq
import cad_to_dagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(assembly, material_tags=["tungsten"])

my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    min_mesh_size=0.5,
    max_mesh_size=10.0,
)
```

**Key parameters:**

- `filename`: Output file path (default: `"dagmc.h5m"`)
- `min_mesh_size`: Minimum mesh element size
- `max_mesh_size`: Maximum mesh element size
- `h5m_backend`: `"h5py"` (default) or `"pymoab"`
- `meshing_backend`: `"gmsh"` (default) or `"cadquery"`

## Unstructured Mesh VTK Files (Volume Mesh)

Creates tetrahedral volume meshes for use with OpenMC's `UnstructuredMesh` tally.

:::{note}
Unstructured mesh output **requires the GMSH backend** - the CadQuery meshing
backend cannot create volume meshes.
:::

```python
import cadquery as cq
import cad_to_dagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(assembly, material_tags=["tungsten"])

my_model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    min_mesh_size=1.0,
    max_mesh_size=5.0,
)
```

**Using in OpenMC:**

<!--pytest-codeblocks:skip-->
```python
import openmc

mesh = openmc.UnstructuredMesh(filename="umesh.vtk", library="moab")
tally = openmc.Tally()
tally.filters = [openmc.MeshFilter(mesh)]
tally.scores = ["flux"]
```

**Selecting specific volumes:**

<!--pytest-codeblocks:skip-->
```python
my_model.export_unstructured_mesh_file(
    filename="partial_mesh.vtk",
    volumes=[1, 3]  # Only include volumes 1 and 3
)
```

## Conformal Surface and Volume Meshes

Create both surface (h5m) and volume (vtk) meshes that share the same surface coordinates.
This is useful when you need both DAGMC geometry and unstructured mesh tallies.

To ensure conformal meshes (where the surface triangles exactly match the volume mesh boundaries),
export both in a single call using the `unstructured_volumes` and `umesh_filename` parameters:

```python
import cadquery as cq
import cad_to_dagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")
assembly.add(cq.Workplane("XY").box(30, 30, 30), name="box")

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(assembly, material_tags=["tungsten", "steel"])

# Export both surface and volume mesh in one call for conformal meshes
dagmc_filename, umesh_filename = my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[1, 2],  # volume IDs to create volume mesh for
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
)
```

:::{note}
The `unstructured_volumes` parameter specifies which volumes should have a tetrahedral
volume mesh created. By exporting both meshes in a single call, the surface triangles
of the DAGMC geometry will exactly match the boundary faces of the volume mesh.
:::

## GMSH Mesh Files

Export the mesh in GMSH's native format for inspection or further processing.

```python
import cadquery as cq
import cad_to_dagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(assembly, material_tags=["tungsten"])

# Export 2D surface mesh
my_model.export_gmsh_mesh_file(
    filename="surface_mesh.msh",
    dimensions=2,
)

# Export 3D volume mesh
my_model.export_gmsh_mesh_file(
    filename="volume_mesh.msh",
    dimensions=3,
)
```

This is useful for:

- Debugging mesh quality
- Using GMSH's visualization tools
- Further mesh processing with other tools
