# Gmsh Backend

The Gmsh backend meshes the geometry with [Gmsh](https://gmsh.info), which is
always installed with cad_to_dagmc. It makes the surface mesh for the DAGMC h5m
file and the tetrahedra for volume meshes, and gives you control over element
sizes and algorithms. Passing any Gmsh argument, such as `min_mesh_size`, makes
`export_dagmc_h5m_file` use this backend; see
[How the Backend Is Chosen](index.md#how-the-backend-is-chosen).

## Basic Usage

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

model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="gmsh",
    min_mesh_size=0.5,
    max_mesh_size=1.0e6,
)
```

## Mesh Size Parameters

`min_mesh_size` and `max_mesh_size` bound the element size:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    min_mesh_size=0.5,   # Minimum element size
    max_mesh_size=10.0,  # Maximum element size
)
```

Smaller sizes give more triangles, which follow the CAD more closely and slow
down particle tracking. Both sizes are in the units of the scaled geometry; see
[Mesh Size and Scaling](../advanced/geometry_scaling.md#mesh-size-and-scaling).
Left at None, Gmsh's own sizing applies, except in
`export_unstructured_mesh_file`, which defaults them to 1 and 5. `set_size`
gives individual volumes their own size; see
[Per-Volume Mesh Sizing](mesh_sizing.md).

## Surface Mesh Algorithms

`mesh_algorithm` sets Gmsh's `Mesh.Algorithm`, the algorithm for the 2D
surface mesh. The tetrahedra have their own setting, `mesh_algorithm_3d`
(below).

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    mesh_algorithm=6,  # Frontal-Delaunay
)
```

| Algorithm | Name | Notes |
|-----------|------|-------|
| 1 | MeshAdapt | cad_to_dagmc's default; the most reliable on complex curved surfaces |
| 2 | Automatic | Delaunay for flat surfaces, MeshAdapt for the others |
| 5 | Delaunay | Fastest for large meshes of flat surfaces |
| 6 | Frontal-Delaunay | Gmsh's own default; try it when element quality matters |

Gmsh also has 7 (BAMG), 8 (Frontal-Delaunay for Quads) and 9 (Packing of
Parallelograms), but with Gmsh 4.15 they failed on simple solids: 7 raised an
error on curved faces, 8 crashed Python on a sphere and 9 did not finish a
plain box in 90 seconds. Try them on a small model first.

Do not use 11 (Quasi-structured Quad). It makes quadrilaterals, and
cad_to_dagmc reads their nodes as triangles. Most exports then raise a
`ValueError`, but a single sphere was exported to a broken h5m file without any
error. See the [Gmsh mesh options](https://gmsh.info/doc/texinfo/gmsh.html#Mesh-options)
for the full list.

## CAD Transfer Method

`method` sets how the geometry gets from CadQuery into Gmsh:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    method="in memory",  # the default is "file"
)
```

`"file"` writes the geometry to a temporary BREP file that Gmsh reads back,
and works with any installation. `"in memory"` passes the OpenCASCADE shape to
Gmsh directly. That skips the file, but Gmsh and CadQuery must be built against
the same OpenCASCADE version, which is easier to arrange with conda than with
pip. With mismatched versions some models transfer and others fail with an
OpenCASCADE exception. Passing `method`, even `"file"`, makes
`export_dagmc_h5m_file` use the Gmsh backend.

## Volume Meshing

Gmsh also makes the tetrahedra for `export_unstructured_mesh_file`,
`export_gmsh_mesh_file(dimensions=3)` and
`export_dagmc_h5m_file(unstructured_volumes=...)`. Examples are on
[Unstructured Mesh VTK Files](../outputs/unstructured_vtk.md) and
[Conformal Meshes](../outputs/conformal_meshes.md).

### 3D Algorithms and Volume-Only Options

`mesh_algorithm_3d` sets Gmsh's `Mesh.Algorithm3D`, independently of the
surface algorithm. The default, `1`, is Delaunay; `10` selects HXT, a parallel
reimplementation of Delaunay. `threads`, an argument of all three export
methods, sets the number of Gmsh threads. Which combination is fastest depends
on the geometry, the settings and the Gmsh build.

`volume_mesh_options` maps Gmsh option names to numbers or strings that apply
to the volume mesh only. When it is given, the export meshes the surfaces
first, sized by `min_mesh_size`, `max_mesh_size` and `set_size`, then sets the
options and meshes the volumes. Relaxing the interior sizing therefore leaves
the surface mesh as it was. For example, HXT with a coarser interior and
Gmsh's tetrahedron optimisation turned off:

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    min_mesh_size=1.0,
    max_mesh_size=5.0,
    mesh_algorithm_3d=10,
    volume_mesh_options={
        "Mesh.Optimize": 0,
        "Mesh.MeshSizeExtendFromBoundary": 0,
        "Mesh.MeshSizeMax": 1e22,
    },
)
```

These settings allow a coarser interior but do not guarantee one, so check the
quality and resolution of the mesh you get. Other Gmsh size limits still apply,
including `Mesh.MeshSizeMin` unless you override it too.

Both arguments work in the three volume exports listed above. In
`export_dagmc_h5m_file` the volumes are filled from the surface mesh already
made for the h5m file. The options apply to every volume alike, and during the
volume step they take precedence over the named arguments, `mesh_algorithm_3d`
included. Gmsh raises an error for an option name it does not recognise and for
a string given to a numeric option. Surface-only exports ignore
`volume_mesh_options`, an empty dictionary changes nothing, and the options do
not carry over to the next export. The cad-to-dagmc-mesher backend ignores both
arguments with a warning.

## Parameters

`export_dagmc_h5m_file`, `export_unstructured_mesh_file` and
`export_gmsh_mesh_file` all take these arguments.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_mesh_size` | float | None; 1 in `export_unstructured_mesh_file` | Smallest element size (`Mesh.MeshSizeMin`). A value above `max_mesh_size` raises `ValueError` |
| `max_mesh_size` | float | None; 5 in `export_unstructured_mesh_file` | Largest element size (`Mesh.MeshSizeMax`) |
| `mesh_algorithm` | int | 1 | 2D surface algorithm (`Mesh.Algorithm`) |
| `mesh_algorithm_3d` | int | 1 | 3D volume algorithm (`Mesh.Algorithm3D`): 1 is Delaunay, 10 is HXT |
| `volume_mesh_options` | dict | None | Gmsh options set after surface meshing, for the volume mesh only |
| `set_size` | dict | None | Target size per volume, keyed by material tag or volume ID; see [Per-Volume Mesh Sizing](mesh_sizing.md) |
| `method` | str | "file" | How the geometry reaches Gmsh: "file" or "in memory" |
| `threads` | int | 0 | Number of Gmsh threads (`General.NumThreads`). 0 uses every logical processor, or `OMP_NUM_THREADS` if it is set. See [Parallel Processing](../advanced/parallel_processing.md#limiting-gmsh-threads) |

An export on this backend closes any gmsh session that is open and starts a
fresh one, so options set with `gmsh.option` before the call are lost. To mesh
with options these arguments do not cover, mesh the model in your own gmsh
session and convert it with `export_gmsh_object_to_dagmc_h5m_file`; see
[From Gmsh Object in Memory](../inputs/gmsh_files.md#from-gmsh-object-in-memory).

## See Also

- [cad-to-dagmc-mesher Backend](cad_to_dagmc_mesher_backend.md): the default meshing backend
- [Per-Volume Mesh Sizing](mesh_sizing.md): sizes for individual volumes
- [Parallel Processing](../advanced/parallel_processing.md): thread and RAM limits
