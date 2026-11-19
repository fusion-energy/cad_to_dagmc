# Meshing Backends

cad_to_dagmc has two meshing backends. Both make the triangle surface mesh that
goes into the DAGMC h5m file, and both can fill volumes with tetrahedra and
write them as a VTK volume mesh.

## Available Backends

| Backend | Description | Best For |
|---------|-------------|----------|
| [cad-to-dagmc-mesher](cad_to_dagmc_mesher_backend.md) | The default. A curvature-adaptive surface mesher with its own tetrahedral mesher, written for DAGMC | Tracking meshes with few triangles |
| [Gmsh](gmsh_backend.md) | An open-source finite-element mesh generator | Setting element sizes, per volume if needed, and choosing algorithms |

## Quick Comparison

| Feature | cad-to-dagmc-mesher | Gmsh |
|---------|---------------------|------|
| Surface mesh (h5m) | Yes | Yes |
| Volume mesh (VTK) | Yes | Yes |
| Mesh size control | `tolerance`, `angular_tolerance`, `target_edge_length` | `min_mesh_size`, `max_mesh_size`, per volume with `set_size` |
| Mesh algorithms | One built-in | Several 2D and 3D algorithms (`mesh_algorithm`, `mesh_algorithm_3d`) |
| Parallel meshing | Yes (`mesh_threads`) | Yes (`threads`) |
| Dependencies | Installed by pip; not on conda-forge | Always installed (a dependency of cad_to_dagmc) |
| Triangles on flat faces | As few as the face needs | Set by the mesh size |

## Choosing a Backend

Use cad-to-dagmc-mesher, the default, unless you need something only Gmsh has.
It follows curved faces to `tolerance` and `angular_tolerance` and covers flat
faces with few triangles, so particles track faster. Solids whose facets fold
back or cross are meshed again at a finer tolerance. A volume mesh needs one
more number, `target_edge_length`.

Use Gmsh to control the elements yourself: a minimum and maximum size, a size
for each volume with `set_size`, or a particular 2D or 3D algorithm. Gmsh is
always installed, while the conda-forge package of cad_to_dagmc comes without
cad-to-dagmc-mesher; see [Optional packages](../installation.md#optional-packages).

## How the Backend Is Chosen

`meshing_backend="cad-to-dagmc-mesher"` or `meshing_backend="gmsh"` picks the
backend. Without it, each export method decides from the other arguments.

`export_dagmc_h5m_file`:

- Any cad-to-dagmc-mesher argument (`tolerance`, `angular_tolerance`,
  `tet_volumes`, `target_edge_length`) selects cad-to-dagmc-mesher.
- Any Gmsh argument (`min_mesh_size`, `max_mesh_size`, `mesh_algorithm`,
  `mesh_algorithm_3d`, `volume_mesh_options`, `set_size`, `method`, `threads`,
  `unstructured_volumes`) selects Gmsh. `umesh_filename` goes with either
  backend; on its own it selects Gmsh.
- Arguments of both kinds raise `ValueError`.
- With none of these arguments it uses cad-to-dagmc-mesher, or Gmsh with a
  warning if cad-to-dagmc-mesher is not installed.

`export_unstructured_mesh_file` uses cad-to-dagmc-mesher only when
`target_edge_length` or `tet_volumes` is given, and Gmsh otherwise.
`export_gmsh_mesh_file` always uses Gmsh.

With `meshing_backend` set, arguments for the other backend are ignored, some
with a warning. The one exception is `unstructured_volumes`, which
`export_dagmc_h5m_file` reads as `tet_volumes` on the cad-to-dagmc-mesher
backend.

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10))

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

# cad-to-dagmc-mesher backend (default)
model.export_dagmc_h5m_file(
    filename="dagmc_mesher.h5m",
    meshing_backend="cad-to-dagmc-mesher",
    tolerance=0.5,
    angular_tolerance=0.2,
)

# Gmsh backend
model.export_dagmc_h5m_file(
    filename="dagmc_gmsh.h5m",
    meshing_backend="gmsh",
    min_mesh_size=0.5,
    max_mesh_size=10.0,
)
```

Each backend sets the mesh size its own way. See the
[cad-to-dagmc-mesher parameters](cad_to_dagmc_mesher_backend.md#parameters) and
the [Gmsh parameters](gmsh_backend.md#parameters). Sizes for individual volumes
are Gmsh only, described in [Per-Volume Mesh Sizing](mesh_sizing.md).
