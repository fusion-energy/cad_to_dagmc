# Gmsh Mesh Files

`export_gmsh_mesh_file()` meshes the geometry with Gmsh and saves the mesh in
Gmsh's own `.msh` format, for inspection, debugging or converting to h5m later.

## Basic Export

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten"])

# Export 2D surface mesh
model.export_gmsh_mesh_file(
    filename="surface_mesh.msh",
    dimensions=2,
    min_mesh_size=0.5,
    max_mesh_size=5.0,
)

# Export 3D volume mesh
model.export_gmsh_mesh_file(
    filename="volume_mesh.msh",
    dimensions=3,
    min_mesh_size=0.5,
    max_mesh_size=5.0,
)
```

`set_size` gives a target size per volume, keyed by material tag or volume ID;
see [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md).

## Viewing and Converting the Mesh

Open the file in the Gmsh GUI to check element sizes and quality, and that the
geometry came through the import intact. The pip `gmsh` package installs the
`gmsh` command:

<!--pytest-codeblocks:skip-->
```bash
gmsh surface_mesh.msh
```

The file has no physical groups, so to convert it to a DAGMC h5m file later,
pass `material_tags` to `export_gmsh_file_to_dagmc_h5m_file()`; see
[Gmsh Files](../inputs/gmsh_files.md).

## API Reference

### `export_gmsh_mesh_file()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filename` | str | `"mesh.msh"` | Output file path |
| `dimensions` | int | `2` | `2` for a surface mesh of triangles, `3` for a volume mesh of tetrahedra |
| `scale_factor` | float | `1.0` | Scales the geometry before meshing. Mesh sizes are in the scaled units; see [Geometry Scaling](../advanced/geometry_scaling.md#mesh-size-and-scaling) |
| `imprint` | str, `None` or `False` | `"partial"` | `"partial"` (default), `"full"`, `None` (imprints without glue) or `False` (no imprint); see [Imprinting](../advanced/imprinting.md) |
| `imprint_threads` | `"all"` or int | `"all"` | `"all"` (default) or a positive int; see [Parallel Processing](../advanced/parallel_processing.md#limiting-imprinting-threads) |

The Gmsh arguments `min_mesh_size`, `max_mesh_size`, `mesh_algorithm`,
`mesh_algorithm_3d`, `volume_mesh_options`, `set_size`, `method` and `threads`
are described under [Gmsh backend parameters](../meshing/gmsh_backend.md#parameters).
`mesh_algorithm_3d` and `volume_mesh_options` only act when `dimensions=3`; see
[3D Algorithms and Volume-Only Options](../meshing/gmsh_backend.md#3d-algorithms-and-volume-only-options).
The [API Reference](../api.md) page has the exact signature.

The method writes the file and returns `None`.

## See Also

- [Gmsh Files](../inputs/gmsh_files.md): converting a Gmsh mesh file to h5m
- [Gmsh documentation](https://gmsh.info/doc/texinfo/gmsh.html): the Gmsh reference manual
