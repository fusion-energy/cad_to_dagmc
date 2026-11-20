# Conformal Meshes

`export_dagmc_h5m_file()` can write a VTK volume mesh along with the DAGMC h5m file, from one meshing run, so that the tetrahedra share the surfaces that particles are tracked on.

OpenMC scores an unstructured mesh tally on the tetrahedra, independently of the DAGMC geometry. When the two meshes share their surfaces, each tetrahedron lies in one DAGMC volume and its result comes from one material. Separate `export_dagmc_h5m_file()` and `export_unstructured_mesh_file()` calls mesh the geometry twice and nothing makes their surfaces match, so tetrahedra near curved boundaries can straddle two volumes.

## Basic Usage

With the default cad-to-dagmc-mesher backend, pass `tet_volumes` and `target_edge_length`, and name the VTK file with `umesh_filename` (default `umesh.vtk`):

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

Given `tet_volumes` and `target_edge_length`, the call returns a `(dagmc_filename, umesh_filename)` tuple. Without them it writes only the h5m file and returns its filename. One without the other raises `ValueError`, and so does `umesh_filename` without both.

For each volume in `tet_volumes` the surface is remeshed at a size based on `target_edge_length`. That surface is written to the h5m file and is also the boundary of the tetrahedra. The volume mesher may split some of its triangles, and on strongly curved faces the tetrahedra can deviate locally from it by up to the chordal error at the tetrahedron edge length. Volumes not in `tet_volumes` keep the curvature-adaptive surface mesh and get no tetrahedra.

`tolerance` and `angular_tolerance` have no effect when every volume is in `tet_volumes`. When some volumes are left out, the two tolerances also size the surfaces of the filled volumes, and so their tetrahedra. The backend's arguments are listed under [cad-to-dagmc-mesher Parameters](../meshing/cad_to_dagmc_mesher_backend.md#parameters).

## Using the Gmsh Backend

With the [Gmsh backend](../meshing/gmsh_backend.md), pass `unstructured_volumes` instead. It takes volume IDs, material tags or a mix, and a tag selects every volume that has it. Prefer tags, because [imprinting](../advanced/imprinting.md#imprinting-and-material-tag-order) can renumber the volumes.

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

dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    unstructured_volumes=[1, "steel"],  # volume 1 and every volume tagged steel
    umesh_filename="umesh.vtk",
    meshing_backend="gmsh",
)
```

Without `unstructured_volumes`, Gmsh writes no VTK file and the call returns only the h5m filename. A call whose only meshing argument is `umesh_filename` runs Gmsh, so it writes no VTK file either.

### How It Works

When you use `unstructured_volumes` on the Gmsh backend:

1. Gmsh generates the surface mesh for all volumes, including shared interfaces
2. Surface triangles are extracted and written to the DAGMC h5m file
3. Any `volume_mesh_options` are applied, then Gmsh generates tetrahedra for the
    selected volumes using the existing surface mesh as their boundary
4. The tetrahedra are written to the VTK file, sharing the surface triangulation
    with the DAGMC geometry

### Controlling the Conformal 3D Mesh

`mesh_algorithm_3d` and `volume_mesh_options` work in the combined export too:

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

The surface mesh written to the h5m file is reused, not regenerated, so the options change only the tetrahedra inside it. Avoid options that change the element order, recombine elements or force a remesh, because the tetrahedra would then no longer match the DAGMC triangles. What each option does, and which settings take precedence, is described under [3D Algorithms and Volume-Only Options](../meshing/gmsh_backend.md#3d-algorithms-and-volume-only-options).

## Complete Example with OpenMC

This example uses the Gmsh backend so that `set_size` can give the middle sphere a finer mesh than its neighbours. Only the middle sphere gets tetrahedra.

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

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])

# Conformal meshes: only the middle sphere gets a volume mesh
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="surface_mesh.h5m",
    set_size={
        "mat1": 0.9,  # coarse mesh for the inner sphere
        "mat2": 0.1,  # fine mesh for the middle sphere, which is tallied
        "mat3": 0.9,  # coarse mesh for the outer sphere
    },
    unstructured_volumes=["mat2"],
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

# Materials, named after the material tags
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

# Settings, with a 14 MeV point source at the centre of the bounding box
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

## See Also

- [DAGMC h5m Files](dagmc_h5m.md): the arguments and return value of `export_dagmc_h5m_file()`
- [Unstructured Mesh VTK Files](unstructured_vtk.md): a volume mesh on its own, and the OpenMC tally
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md): `set_size` on the Gmsh backend
