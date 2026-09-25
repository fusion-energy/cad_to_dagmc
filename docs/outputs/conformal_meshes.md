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

Export both meshes in a single call with the cad-to-dagmc-mesher backend (the default) using `tet_volumes`, `target_edge_length` and `umesh_filename`:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere = cq.Workplane("XY").sphere(10)
box = cq.Workplane("XY").box(30, 30, 30).cut(sphere)

assembly = cq.Assembly()
assembly.add(sphere, name="sphere")
assembly.add(box, name="box")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten", "steel"])

# Export both meshes in one call
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    tet_volumes=["tungsten", "steel"],  # material tags of volumes to fill with tetrahedra
    target_edge_length=2.0,
    umesh_filename="umesh.vtk",
)
```

For each volume listed in `tet_volumes` the surface is remeshed to near-equilateral triangles at `target_edge_length`, and that surface becomes both the DAGMC tracking surface and the tetrahedra boundary, so the two meshes share the same surface (individual surface triangles may be subdivided in the volume mesh, and on high curvature faces small local deviations up to the chordal error of the tetrahedron edge length can occur). Volumes not listed keep the curvature-adaptive surface mesh and get no tetrahedra. See the [cad-to-dagmc-mesher backend](../meshing/cad_to_dagmc_mesher_backend.md) for the other options.

## Using the GMSH Backend

The [GMSH backend](../meshing/gmsh_backend.md) produces conformal meshes with the `unstructured_volumes` parameter instead:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[1, 2],  # Volumes to include in VTK mesh
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
)
```

### Controlling the Conformal 3D Mesh

`mesh_algorithm_3d` and `volume_mesh_options` apply to this combined export as
well as standalone `export_unstructured_mesh_file()` and
`export_gmsh_mesh_file(dimensions=3)` calls:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
    unstructured_volumes=["tungsten", "steel"],
    min_mesh_size=1.0,
    max_mesh_size=5.0,
    mesh_algorithm_3d=10,  # HXT; default 1 selects Delaunay
    volume_mesh_options={
        "Mesh.Optimize": 0,
        "Mesh.MeshSizeExtendFromBoundary": 0,
        "Mesh.MeshSizeMax": 1e22,
    },
)
```

The DAGMC surface is generated first with the normal surface sizing, then the
overrides are applied before filling the selected volumes with tetrahedra.
The existing surface triangulation is reused, not independently regenerated.
These settings allow a coarser interior; they do not guarantee zero refinement.
Avoid options that change element order, recombine elements or force remeshing
when you need the first-order tetrahedral boundary to match the DAGMC triangles.

Separate surface and volume export calls do not share mesh state, even when
their sizes are identical. Use the combined export when matching the tracking
and tally boundaries is required. See
[3D algorithms and volume-only options](../meshing/gmsh_backend.md#3d-algorithms-and-volume-only-options)
for defaults and precedence rules.

### Selecting Volumes for Volume Mesh

#### By Volume ID

`unstructured_volumes` accepts volume IDs, material tag names, or a mix of both. Specify which volumes should have a volume mesh:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[2],  # Only volume 2 gets volume mesh
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
)
```

#### By Material Tag Name

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

#### Mixed IDs and Names

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

### How It Works

When you use `unstructured_volumes` on the GMSH backend:

1. GMSH generates the surface mesh for all volumes, including shared interfaces
2. Surface triangles are extracted and written to the DAGMC h5m file
3. Any `volume_mesh_options` are applied, then GMSH generates tetrahedra for the
    selected volumes using the existing surface mesh as their boundary
4. The tetrahedra are written to the VTK file, sharing the surface triangulation
    with the DAGMC geometry

This guarantees:
- Surface triangles match volume mesh boundaries
- No gaps or overlaps between meshes
- Consistent particle tracking and tallying

## Complete Example with OpenMC

This example uses the GMSH backend so that `set_size` can give the middle sphere a finer mesh than its neighbours.

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

## API Notes

When `tet_volumes` and `target_edge_length` (or `unstructured_volumes` on the GMSH backend) are specified, `export_dagmc_h5m_file()` returns a tuple:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    tet_volumes=["steel"],
    target_edge_length=2.0,
    umesh_filename="umesh.vtk",
)
```

Without them, it returns just the filename:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename = model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

## See Also

- [DAGMC H5M](dagmc_h5m.md) - Surface mesh output details
- [Unstructured VTK](unstructured_vtk.md) - Volume mesh output details
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Control mesh density
