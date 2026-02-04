# Conformal Meshes

Create both surface (h5m) and volume (vtk) meshes that share the same surface coordinates. This ensures the surface triangles exactly match the volume mesh boundaries.

## Why Conformal Meshes?

When running neutronics simulations with both:
- DAGMC geometry (surface mesh for particle tracking)
- Unstructured mesh tallies (volume mesh for scoring)

The meshes should be **conformal** - the surface triangles of the DAGMC geometry should exactly match the boundary faces of the volume mesh. This avoids:
- Particles crossing mesh boundaries incorrectly
- Numerical artifacts at interfaces
- Inconsistent tallying near surfaces

## Basic Usage

Export both meshes in a single call using `unstructured_volumes` and `umesh_filename`:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")
assembly.add(cq.Workplane("XY").box(30, 30, 30), name="box")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten", "steel"])

# Export both meshes in one call
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[1, 2],  # Volumes to include in VTK mesh
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",  # must use gmsh backend for conformal surface and volume meshing
)
```

## Selecting Volumes for Volume Mesh

### By Volume ID

Specify which volumes should have a volume mesh:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[2],  # Only volume 2 gets volume mesh
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
)
```

### By Material Tag Name

Use material tag names instead of IDs:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=["steel"],  # All volumes with "steel" tag
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
)
```

### Mixed IDs and Names

Combine volume IDs and material tag names:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[1, "tungsten"],  # Volume 1 and all tungsten volumes
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
)
```

## Complete Example with OpenMC

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc
import openmc

# Create half-sphere geometry
box_cutter = cq.Workplane("XY").moveTo(0, 5).box(20, 10, 20)
inner_sphere = cq.Workplane("XY").sphere(6).cut(box_cutter)
middle_sphere = cq.Workplane("XY").sphere(6.1).cut(box_cutter).cut(inner_sphere)
outer_sphere = (
    cq.Workplane("XY").sphere(10).cut(box_cutter).cut(inner_sphere).cut(middle_sphere)
)

assembly = cq.Assembly()
assembly.add(inner_sphere, name="inner_sphere")
assembly.add(middle_sphere, name="middle_sphere")
assembly.add(outer_sphere, name="outer_sphere")

# Create conformal meshes - only middle sphere gets volume mesh
model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])

dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="surface_mesh.h5m",
    set_size={
        1: 0.9,  # Coarse mesh for inner
        2: 0.1,  # Fine mesh for middle (where we want detailed tallies)
        3: 0.9,  # Coarse mesh for outer
    },
    unstructured_volumes=[2],  # Only middle sphere in volume mesh
    umesh_filename="volume_mesh.vtk",
    meshing_backend="gmsh",
)

# Set up OpenMC with unstructured mesh tally
umesh = openmc.UnstructuredMesh(umesh_filename, library="moab")
mesh_filter = openmc.MeshFilter(umesh)
tally = openmc.Tally(name="unstructured_mesh_tally")
tally.filters = [mesh_filter]
tally.scores = ["flux"]
tallies = openmc.Tallies([tally])

# Materials
mat1 = openmc.Material(name="mat1")
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)

mat2 = openmc.Material(name="mat2")
mat2.add_nuclide("H1", 1, percent_type="ao")
mat2.set_density("g/cm3", 0.002)

mat3 = openmc.Material(name="mat3")
mat3.add_nuclide("H1", 1, percent_type="ao")
mat3.set_density("g/cm3", 0.003)

materials = openmc.Materials([mat1, mat2, mat3])

# DAGMC geometry
dag_univ = openmc.DAGMCUniverse(filename=dagmc_filename)
geometry = openmc.Geometry(root=dag_univ.bounded_universe())

# Settings
settings = openmc.Settings()
settings.batches = 10
settings.particles = 5000
settings.run_mode = "fixed source"

source = openmc.IndependentSource()
source.space = openmc.stats.Point(geometry.bounding_box.center)
source.angle = openmc.stats.Isotropic()
source.energy = openmc.stats.Discrete([14e6], [1])
settings.source = source

# Run
model = openmc.Model(geometry, materials, settings, tallies)
sp_filename = model.run()
```

## How It Works

When you use `unstructured_volumes`:

1. GMSH creates a unified mesh for all volumes
2. Surface triangles are extracted for the DAGMC h5m file
3. Volume tetrahedra are extracted for the specified volumes
4. Both share the same surface coordinates at interfaces

This guarantees:
- Surface triangles match volume mesh boundaries
- No gaps or overlaps between meshes
- Consistent particle tracking and tallying

## API Notes

When `unstructured_volumes` is specified, `export_dagmc_h5m_file()` returns a tuple:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[1, 2],
    umesh_filename="umesh.vtk",
)
```

Without `unstructured_volumes`, it returns just the filename:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename = model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

## See Also

- [DAGMC H5M](dagmc_h5m.md) - Surface mesh output details
- [Unstructured VTK](unstructured_vtk.md) - Volume mesh output details
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Control mesh density
