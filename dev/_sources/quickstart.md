# Quickstart

This page shows the simplest way to create a DAGMC h5m file from a CadQuery object.

## Basic Example

Create a simple geometry and convert it to DAGMC format:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create some geometry with CadQuery
sphere = cq.Workplane("XY").sphere(10)
box = cq.Workplane("XY").box(30, 30, 30)

# Create an assembly
assembly = cq.Assembly()
assembly.add(sphere, name="sphere")
assembly.add(box, name="box")

# Convert to DAGMC
model = CadToDagmc()
model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags=["tungsten", "steel"]
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

This creates a `dagmc.h5m` file with two volumes tagged with materials
`mat:tungsten` and `mat:steel`.

## From a STEP File

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_stp_file(
    filename="geometry.step",
    material_tags=["mat1", "mat2", "mat3"]
)
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

## Creating a Volume Mesh

Create a tetrahedral volume mesh (VTK format) for use with OpenMC's unstructured mesh tallies:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create geometry
sphere = cq.Workplane("XY").sphere(10)

assembly = cq.Assembly()
assembly.add(sphere, name="sphere")

# Convert to unstructured mesh
model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten"])

model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    min_mesh_size=1.0,
    max_mesh_size=5.0,
)
```

:::{note}
Volume mesh export requires the GMSH meshing backend, which is used by default.
The CadQuery backend only supports surface meshes.
:::

## Creating Conformal Surface and Volume Meshes

For neutronics simulations that use both DAGMC geometry and unstructured mesh tallies,
you can create conformal meshes where the surface and volume meshes share the same
boundary coordinates. This is done in a single export call using the `unstructured_volumes`
parameter:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create geometry
assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")
assembly.add(cq.Workplane("XY").box(30, 30, 30), name="box")

# Convert to DAGMC
model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten", "steel"])

# Export both surface mesh and volume mesh in one call
# This ensures the meshes are conformal (share the same boundary)
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
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

## Using in OpenMC

Once you have a DAGMC h5m file, you can use it in OpenMC:

<!--pytest-codeblocks:skip-->
```python
import openmc

# Define materials (names must match material tags)
tungsten = openmc.Material(name="tungsten")
tungsten.add_element("W", 1.0)
tungsten.set_density("g/cm3", 19.3)

steel = openmc.Material(name="steel")
steel.add_element("Fe", 1.0)
steel.set_density("g/cm3", 7.8)

materials = openmc.Materials([tungsten, steel])

# Load the DAGMC geometry
dag_universe = openmc.DAGMCUniverse(filename="dagmc.h5m")
geometry = openmc.Geometry(root=dag_universe)

# Set up settings
settings = openmc.Settings()
settings.batches = 10
settings.particles = 1000
settings.run_mode = "fixed source"

# ... continue with source definition, tallies, etc.
```

Using unstructured mesh tallies:

<!--pytest-codeblocks:skip-->
```python
import openmc

# Create mesh from VTK file
mesh = openmc.UnstructuredMesh(filename="umesh.vtk", library="moab")

# Create tally with mesh filter
mesh_filter = openmc.MeshFilter(mesh)
tally = openmc.Tally()
tally.filters = [mesh_filter]
tally.scores = ["flux", "heating"]

tallies = openmc.Tallies([tally])
```
