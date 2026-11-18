# DAGMC h5m Files

`export_dagmc_h5m_file()` writes the geometry as a DAGMC h5m file, a triangle
surface mesh with a material tag on every volume. DAGMC-enabled transport codes
(OpenMC, MCNP, FLUKA and others) track particles through it.

## Basic Export

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

model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

With no meshing arguments, the cad-to-dagmc-mesher backend meshes the geometry
and the h5py backend writes the file. Any Gmsh argument, such as
`max_mesh_size`, switches meshing to Gmsh; see
[How the Backend Is Chosen](../meshing/index.md#how-the-backend-is-chosen).
To write the file with MOAB's own library instead, install pymoab and pass
`h5m_backend="pymoab"`; see [h5m Backends](../advanced/h5m_backends.md).

## API Reference

### `export_dagmc_h5m_file()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filename` | str | `"dagmc.h5m"` | Output file path |
| `implicit_complement_material_tag` | str | `None` | Material for the implicit complement, the space between and around the volumes. See [Implicit Complement](../advanced/implicit_complement.md) |
| `scale_factor` | float | `1.0` | Scales the geometry before meshing. Linear mesh sizes are in the scaled units; see [Geometry Scaling](../advanced/geometry_scaling.md#mesh-size-and-scaling) |
| `imprint` | str, `None` or `False` | `"partial"` | `"partial"` (default), `"full"`, `None` (imprints without glue) or `False` (no imprint); see [Imprinting](../advanced/imprinting.md) |
| `imprint_threads` | `"all"` or int | `"all"` | `"all"` (default) or a positive int; see [Parallel Processing](../advanced/parallel_processing.md#limiting-imprinting-threads) |
| `meshing_backend` | str | chosen from the other arguments | `"cad-to-dagmc-mesher"` or `"gmsh"`; see [How the Backend Is Chosen](../meshing/index.md#how-the-backend-is-chosen) |
| `h5m_backend` | str | `"h5py"` | `"h5py"` or `"pymoab"`; see [h5m Backends](../advanced/h5m_backends.md) |
| `tet_volumes` | list of str | `None` | cad-to-dagmc-mesher: material tags of the volumes to fill with tetrahedra. Needs `target_edge_length` |
| `target_edge_length` | float | `None` | cad-to-dagmc-mesher: target tetrahedron edge length, in scaled units. Needs `tet_volumes` |
| `unstructured_volumes` | list of int or str | `None` | Gmsh: volume IDs or material tags of the volumes to fill with tetrahedra |
| `umesh_filename` | str | `"umesh.vtk"` | Path of the VTK volume mesh |

Passing `tet_volumes` and `target_edge_length`, or `unstructured_volumes`, also
writes a VTK volume mesh to `umesh_filename` that shares its surfaces with the
h5m file; see [Conformal Meshes](conformal_meshes.md). On the
cad-to-dagmc-mesher backend, `tet_volumes` or `target_edge_length` without the
other raises `ValueError`, and so does `umesh_filename` without both.

The other meshing arguments are described on the backend pages:
[cad-to-dagmc-mesher parameters](../meshing/cad_to_dagmc_mesher_backend.md#parameters)
(`tolerance`, `angular_tolerance`, `mesh_threads`) and
[Gmsh parameters](../meshing/gmsh_backend.md#parameters) (`min_mesh_size`,
`max_mesh_size`, `set_size`, `threads` and others). The
[API Reference](../api.md) page has the exact signature.

`export_dagmc_h5m_file()` returns the h5m filename, or a
`(filename, umesh_filename)` tuple when it also writes a volume mesh.

## Using in OpenMC

<!--pytest-codeblocks:skip-->
```python
import openmc

# Material names must match the material tags
tungsten = openmc.Material(name="tungsten")
tungsten.add_element("W", 1.0)
tungsten.set_density("g/cm3", 19.3)

steel = openmc.Material(name="steel")
steel.add_element("Fe", 1.0)
steel.set_density("g/cm3", 7.8)

materials = openmc.Materials([tungsten, steel])

# cad_to_dagmc writes no graveyard, so bounded_universe() puts the geometry
# inside a box with a vacuum boundary
dag_universe = openmc.DAGMCUniverse(filename="dagmc.h5m")
geometry = openmc.Geometry(root=dag_universe.bounded_universe())

settings = openmc.Settings()
settings.batches = 10
settings.particles = 1000
settings.run_mode = "fixed source"
# Set settings.source here. Without one, OpenMC starts particles from a point
# at the origin with a Watt fission spectrum.

model = openmc.Model(geometry=geometry, materials=materials, settings=settings)
model.run()
```

This loads the file from [Basic Export](#basic-export). For a complete run with
a source and an unstructured mesh tally, see
[Complete Example with OpenMC](conformal_meshes.md#complete-example-with-openmc).

## See Also

- [h5m Backends](../advanced/h5m_backends.md): writing with h5py or pymoab
- [cad-to-dagmc-mesher Backend](../meshing/cad_to_dagmc_mesher_backend.md): the default meshing backend
- [Gmsh Backend](../meshing/gmsh_backend.md): Gmsh meshing options
- [Checking for Overlaps](../advanced/overlaps.md): the overlaps an export refuses, and finding the rest
