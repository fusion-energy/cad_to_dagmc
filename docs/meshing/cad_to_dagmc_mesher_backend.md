# cad-to-dagmc-mesher Backend

The [cad-to-dagmc-mesher](https://github.com/fusion-energy/cad-to-dagmc-mesher) backend, the default, is a mesher written for DAGMC geometry. It creates triangle surface meshes using constrained Delaunay triangulation and can also fill volumes with tetrahedra, so it produces both the DAGMC h5m file and a VTK volume mesh. It is installed by pip with cad_to_dagmc, but conda-forge does not have it; see [Optional packages](../installation.md#optional-packages).

## Why a Neutronics-Specific Mesh?

Finite-element meshes generally aim for regularly sized, near-equilateral
elements throughout every surface, because element shape and size affect the
accuracy of field interpolation.

DAGMC surface meshes serve a different purpose: particle tracking only needs
a conforming, watertight representation of each boundary. A neutronics mesh
can therefore preserve curved geometry to the requested tolerance while
representing large planar regions with very few triangles. Fewer triangles
mean fewer candidate intersections during tracking.

The comparison below meshes a cube with an embedded sphere both ways. The
neutronics mesh gets closer to the true volumes with about half the triangles,
and the right-hand panel shows OpenMC tracking speed falling as the triangle
count grows.

```{image} ../_static/mesher_comparison.png
:alt: Three-panel comparison. A uniformly triangulated FEM mesh with box and sphere volume accuracy is on the left, a curvature-adaptive neutronics mesh with minimally triangulated planar cube faces and volume accuracy is in the middle, and measured OpenMC particle throughput versus triangle count is on the right.
:width: 100%
```

## Surface Mesh (h5m)

This backend and both tolerances below are the defaults, so
`model.export_dagmc_h5m_file(filename="dagmc.h5m")` gives the same mesh.

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10))

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="cad-to-dagmc-mesher",
    tolerance=0.5,
    angular_tolerance=0.2,
)
```

## Volume Mesh (VTK)

`export_unstructured_mesh_file` writes the tetrahedra to a VTK file for
`openmc.UnstructuredMesh(filename, library="moab")`. `target_edge_length` is
required and selects this backend. `tet_volumes` limits the mesh to the volumes
with those material tags (default: every volume). Passing it without
`target_edge_length` raises `ValueError`.

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    target_edge_length=2.0,
)
```

`export_dagmc_h5m_file` writes the h5m file and a conformal volume mesh from
one meshing pass when given both `tet_volumes` and `target_edge_length`, and
then returns a `(dagmc_filename, umesh_filename)` tuple. See
[Conformal Meshes](../outputs/conformal_meshes.md).

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tolerance` | float | 0.5 | Largest distance between the surface mesh and the CAD surface (linear deflection), in the units of the scaled geometry |
| `angular_tolerance` | float | 0.2 | Largest angle, in radians, between the normals of neighbouring facets on a curved face (angular deflection) |
| `target_edge_length` | float | None | Target edge length of the tetrahedra, in the units of the scaled geometry. Needed for a volume mesh. A length that would put more than 20 million points inside one solid raises `ValueError` |
| `tet_volumes` | list of str | None | Material tags of the volumes to fill with tetrahedra. Their surfaces are remeshed for `target_edge_length`, and `tolerance` and `angular_tolerance` affect them only when some volumes are left unfilled. None means every volume in `export_unstructured_mesh_file`. In `export_dagmc_h5m_file` None means no volume mesh, and `target_edge_length` without `tet_volumes` raises `ValueError` |
| `mesh_threads` | int or "all" | "all" | Threads for the meshing after the imprint; fewer threads lower the peak RAM. See [Parallel Processing](../advanced/parallel_processing.md#limiting-cad-to-dagmc-mesher-meshing-threads) |

`scale_factor` is applied before meshing, so with `scale_factor=100` (metres
to centimetres) the default `tolerance` of 0.5 is 5 mm.
[Mesh Size and Scaling](../advanced/geometry_scaling.md#mesh-size-and-scaling)
has the details.

Passing `tolerance`, `angular_tolerance`, `target_edge_length` or `tet_volumes`
makes `export_dagmc_h5m_file` use this backend. `export_unstructured_mesh_file`
switches to it only for `target_edge_length` or `tet_volumes`. See
[How the Backend Is Chosen](index.md#how-the-backend-is-chosen).

### Choosing Tolerances

The defaults, `tolerance=0.5` and `angular_tolerance=0.2`, kept every solid's
volume within 0.2% and lost no particles on large imported B-spline models. On
curved faces it is the angular tolerance that limits the facets. Set it too
loose and the two faces of a thin wall can be meshed through each other: at
0.5 rad, a 0.7 cm wall's faces crossed. The mesher finds such solids and
refines them, but a smaller angular tolerance avoids the extra rounds.

After meshing, any solid whose facets fold back, or whose surface crosses
itself, is meshed again at a finer tolerance, up to four more times, and the
best mesh is kept. If a round would not fit in the free memory, the export
raises `RefinementMemoryError` rather than return a less refined mesh.
`model.refinement` holds the report of the last `export_dagmc_h5m_file` call:
the rounds used, whether it converged, and each solid's final tolerances. It is
None after a Gmsh export.

## Limitations

| Limitation | Impact |
|------------|--------|
| No per-volume sizing | `set_size` is not supported; the tolerances apply to every solid |
| Single tetrahedron size | One `target_edge_length` for all volumes |
| No mesh algorithm choice | One built-in method |

## See Also

- [Gmsh Backend](gmsh_backend.md): the other meshing backend
- [Unstructured Mesh VTK Files](../outputs/unstructured_vtk.md): writing and using the volume mesh
- [Conformal Meshes](../outputs/conformal_meshes.md): surface and volume meshes from one call
