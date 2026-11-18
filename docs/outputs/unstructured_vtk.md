# Unstructured Mesh VTK Files

`export_unstructured_mesh_file()` writes a volume mesh of tetrahedra to a VTK file, for unstructured mesh tallies in OpenMC.

Both meshing backends can write it. Unless `meshing_backend` is set, passing `target_edge_length` or `tet_volumes` selects cad-to-dagmc-mesher and any other call runs Gmsh. This differs from `export_dagmc_h5m_file()`, which defaults to cad-to-dagmc-mesher; see [How the Backend Is Chosen](../meshing/index.md#how-the-backend-is-chosen).

## Basic Export

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten"])

model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    target_edge_length=2.0,
)
```

`target_edge_length` sizes the tetrahedra and selects the [cad-to-dagmc-mesher backend](../meshing/cad_to_dagmc_mesher_backend.md). Every volume is filled unless `tet_volumes` lists the material tags of the volumes to fill:

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    target_edge_length=2.0,
    tet_volumes=["tungsten"],
)
```

`tet_volumes` without `target_edge_length` raises `ValueError`.

`tolerance` and `angular_tolerance` have no effect when every volume is filled, which is the default. When `tet_volumes` leaves some volumes out, the two tolerances also size the surfaces of the filled volumes, and so their tetrahedra.

## Using the Gmsh Backend

Without `target_edge_length` or `tet_volumes` the [Gmsh backend](../meshing/gmsh_backend.md) runs, and sizes the tetrahedra with `min_mesh_size` and `max_mesh_size`. Here they default to 1 and 5, whereas `export_dagmc_h5m_file()` leaves the sizes to Gmsh. `volumes` limits the mesh to the listed volume IDs:

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    min_mesh_size=1.0,
    max_mesh_size=5.0,
    volumes=[1, 3],  # omit to mesh every volume
)
```

`volumes` accepts volume IDs only, and cad-to-dagmc-mesher ignores it without a warning. To select volumes by material tag, use `tet_volumes` with the cad-to-dagmc-mesher backend, as above.

`mesh_algorithm_3d` and `volume_mesh_options` control how Gmsh fills the volumes; see [3D Algorithms and Volume-Only Options](../meshing/gmsh_backend.md#3d-algorithms-and-volume-only-options).

## API Reference

### `export_unstructured_mesh_file()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filename` | str | `"umesh.vtk"` | Output file. Must end in `.vtk`, otherwise `ValueError` is raised |
| `scale_factor` | float | `1.0` | Scales the geometry before meshing, so mesh sizes are in scaled units; see [Geometry Scaling](../advanced/geometry_scaling.md#mesh-size-and-scaling) |
| `imprint` | str, `None` or `False` | `"partial"` | `"partial"` (default), `"full"`, `None` (imprints without glue) or `False` (no imprint); see [Imprinting](../advanced/imprinting.md) |
| `imprint_threads` | `"all"` or int | `"all"` | `"all"` (default) or a positive int; see [Parallel Processing](../advanced/parallel_processing.md#limiting-imprinting-threads) |
| `meshing_backend` | str | `None` | `"cad-to-dagmc-mesher"` or `"gmsh"`. When not set, cad-to-dagmc-mesher if `target_edge_length` or `tet_volumes` is given, otherwise Gmsh |
| `target_edge_length` | float | `None` | Target edge length of the tetrahedra (cad-to-dagmc-mesher, which requires it) |
| `tet_volumes` | list of str | `None` | Material tags of the volumes to fill (cad-to-dagmc-mesher). `None` fills every volume |
| `volumes` | list of int | `None` | Volume IDs to mesh (Gmsh). `None` meshes every volume |

The method returns `filename`. The other meshing arguments are listed on each backend's page: `tolerance`, `angular_tolerance` and `mesh_threads` in the [cad-to-dagmc-mesher table](../meshing/cad_to_dagmc_mesher_backend.md#parameters), and `min_mesh_size`, `max_mesh_size`, `mesh_algorithm`, `mesh_algorithm_3d`, `volume_mesh_options`, `set_size`, `method` and `threads` in the [Gmsh table](../meshing/gmsh_backend.md#parameters). The [API Reference](../api.md) page has the exact signature.

## Using in OpenMC

Load the VTK file as an OpenMC unstructured mesh and tally on it:

<!--pytest-codeblocks:skip-->
```python
import openmc

mesh = openmc.UnstructuredMesh(filename="umesh.vtk", library="moab")

mesh_filter = openmc.MeshFilter(mesh)
tally = openmc.Tally()
tally.filters = [mesh_filter]
tally.scores = ["flux", "heating"]

tallies = openmc.Tallies([tally])
```

[Complete Example with OpenMC](conformal_meshes.md#complete-example-with-openmc) builds a whole model around such a tally, with materials, a source and the run.

## See Also

- [Conformal Meshes](conformal_meshes.md): an h5m file and a VTK file from one meshing run
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md): `set_size` on the Gmsh backend
- [cad-to-dagmc-mesher Backend](../meshing/cad_to_dagmc_mesher_backend.md): how the mesher builds the surfaces and tetrahedra
- [Gmsh Backend](../meshing/gmsh_backend.md): Gmsh meshing options
