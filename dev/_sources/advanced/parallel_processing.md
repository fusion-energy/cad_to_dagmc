# Parallel Processing

Imprinting and meshing run on several threads, and the peak RAM of each step
grows with its thread count. Each step has its own limit:

| Step | Argument | Default |
|------|----------|---------|
| Imprinting (OpenCASCADE) | `imprint_threads` | `"all"`: every logical processor |
| Meshing with cad-to-dagmc-mesher | `mesh_threads` | `"all"`: every logical processor, unless `RAYON_NUM_THREADS` is set |
| Meshing with Gmsh | `threads` | `0`: every logical processor, unless `OMP_NUM_THREADS` is set |

All three are arguments of `export_dagmc_h5m_file` and
`export_unstructured_mesh_file`. `export_gmsh_mesh_file`, which always meshes
with Gmsh, takes `imprint_threads` and `threads`. A limit applies to its own
step only and is undone afterwards. Fewer threads lower the peak RAM at the
cost of speed, which helps on a shared machine or when an export runs out of
memory.

To run every step on four threads, with each meshing backend:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

box = cq.Workplane().box(10, 10, 10)
lid = cq.Workplane().box(10, 10, 2).translate((0, 0, 6))

model = CadToDagmc()
model.add_cadquery_object(box, material_tags=["steel"])
model.add_cadquery_object(lid, material_tags=["copper"])

# cad-to-dagmc-mesher backend, the default
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint_threads=4,
    mesh_threads=4,
)

# Gmsh backend
model.export_dagmc_h5m_file(
    filename="dagmc_gmsh.h5m",
    meshing_backend="gmsh",
    imprint_threads=4,
    threads=4,
)
```

## Limiting Imprinting Threads

Imprinting is usually the step that needs the most memory. `imprint_threads`
sets the size of the OpenCASCADE thread pool for the imprint only, with either
meshing backend:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint_threads=1,  # lowest peak RAM, slowest imprint
)
```

It takes `"all"` (the default) or a positive int. `"all"` asks for every
logical processor, even if you limited the pool earlier with `setThreads`. The
previous pool size is restored after the imprint, including when it raises.
[Imprinting](imprinting.md) covers the imprint itself.

## Limiting cad-to-dagmc-mesher Meshing Threads

After the imprint, the cad-to-dagmc-mesher backend meshes in parallel: the
surface triangulation, the edge discretisation, merging and repair, the mesh
checks and any tetrahedral meshing. `mesh_threads` runs all of that on a pool
of the given size. It takes `"all"` (the default) or a positive int, and the
mesh is the same on any number of threads.

With `"all"` the mesher keeps its default thread pool, which has one thread per
logical processor unless the `RAYON_NUM_THREADS` environment variable is set.
The Gmsh backend ignores `mesh_threads` with a warning.

## Limiting Gmsh Threads

The Gmsh backend takes `threads`, which sets Gmsh's `General.NumThreads`
option. The default, 0, uses `OMP_NUM_THREADS` if it is set and otherwise every
logical processor.

`threads` is a Gmsh argument, so passing it to `export_dagmc_h5m_file` selects
the Gmsh backend, as described in
[How the Backend Is Chosen](../meshing/index.md#how-the-backend-is-chosen). To
limit the default backend, use `mesh_threads`.

Each export that meshes with Gmsh starts a new gmsh session, so a
`General.NumThreads` set with `gmsh.option.setNumber` before the call is lost.
Pass `threads` instead.

## Limiting CadQuery Threads

Your own CadQuery operations, such as the booleans that build a model, run on
the same OpenCASCADE pool as the imprint. `setThreads` sets its size until you
change it again:

<!--pytest-codeblocks:skip-->
```python
from cadquery.occ_impl.shapes import setThreads

setThreads(4)
```

This does not limit the imprint inside an export, which `imprint_threads`
controls. `OMP_NUM_THREADS` does not change this pool.

## See Also

- [Imprinting](imprinting.md): what the imprint does and how to configure it
- [cad-to-dagmc-mesher Backend](../meshing/cad_to_dagmc_mesher_backend.md): the mesher's other arguments
- [Gmsh Backend](../meshing/gmsh_backend.md): the other Gmsh arguments
