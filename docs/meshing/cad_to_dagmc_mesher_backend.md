# cad-to-dagmc-mesher Backend

The [cad-to-dagmc-mesher](https://github.com/fusion-energy/cad-to-dagmc-mesher) backend is a purpose-built mesher for DAGMC geometry. It creates triangle surface meshes using constrained Delaunay triangulation and can also fill volumes with tetrahedra, so it can produce both DAGMC h5m files and unstructured volume mesh vtk files without GMSH. It is installed automatically as a dependency of cad_to_dagmc.

## Surface Mesh (h5m)

<!--pytest-codeblocks:skip-->
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
    tolerance=0.01,
    angular_tolerance=0.2,
)
```

## Volume Mesh (vtk)

The backend can write a tetrahedral unstructured volume mesh for use with
`openmc.UnstructuredMesh(filename, library="moab")`:

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    meshing_backend="cad-to-dagmc-mesher",
    target_edge_length=2.0,
)
```

Passing `target_edge_length` (or `tet_volumes`) selects this backend automatically, so `meshing_backend` can be omitted:

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    target_edge_length=2.0,
)
```

## Surface and Volume Mesh in One Call

`export_dagmc_h5m_file` can write the DAGMC h5m file and the unstructured volume mesh vtk file from a single meshing call. The two meshes are conformal: for tet-meshed volumes the surface is remeshed to near-equilateral triangles at `target_edge_length`, that surface is used as the DAGMC tracking surface, and the volume mesher fills it with tetrahedra whose boundary follows that surface (individual surface triangles may be subdivided in the volume mesh, and on high curvature faces small local deviations up to the chordal error of the tetrahedron edge length can occur). Provide both `tet_volumes` and `target_edge_length` and the export returns a `(dagmc_filename, umesh_filename)` tuple:

<!--pytest-codeblocks:skip-->
```python
dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    tet_volumes=["mat1"],       # material tag names of volumes to fill with tets
    target_edge_length=2.0,
    umesh_filename="umesh.vtk",
)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tolerance` | float | 0.01 | Linear deflection tolerance for the surface mesh |
| `angular_tolerance` | float | 0.2 | Angular deflection tolerance for the surface mesh |
| `target_edge_length` | float | None | Target tetrahedron edge length for the volume mesh |
| `tet_volumes` | Iterable[str] | None | Material tag names of the volumes to fill with tetrahedra |

**Tolerance explanation:**
- `tolerance` controls how far the surface mesh can deviate from the true surface (linear distance)
- `angular_tolerance` controls the maximum angle between adjacent facet normals
- `target_edge_length` controls the size of the tetrahedra in the volume mesh

## Backend Auto-Selection

When `meshing_backend` is not given, the tet arguments select this backend automatically:

- `export_unstructured_mesh_file(..., target_edge_length=...)` uses cad-to-dagmc-mesher; without tet arguments it uses gmsh.
- `export_dagmc_h5m_file(..., tet_volumes=..., target_edge_length=...)` uses cad-to-dagmc-mesher; mixing these with gmsh-specific arguments (for example `min_mesh_size`) raises an error asking for an explicit `meshing_backend`.

## Advantages

| Advantage | Explanation |
|-----------|-------------|
| Volume meshes without GMSH | Writes the vtk file directly |
| One meshing call for both outputs | h5m and vtk come from the same mesh |
| Simple configuration | Two surface tolerances plus one tet edge length |
| Installed with cad_to_dagmc | No extra dependency to install |

## Limitations

| Limitation | Impact |
|------------|--------|
| No per-volume sizing | `set_size` parameter is not supported |
| Single tet size | One `target_edge_length` for all volumes |
| No mesh algorithm choice | One built-in method |

## See Also

- [GMSH Backend](gmsh_backend.md) - Full-featured meshing backend
- [CadQuery Backend](cadquery_backend.md) - Surface-only tessellation backend
- [Unstructured VTK](../outputs/unstructured_vtk.md) - Volume mesh output details
- [Conformal Meshes](../outputs/conformal_meshes.md) - Matching surface and volume meshes
