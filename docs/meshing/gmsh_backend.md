# GMSH Backend

The GMSH backend provides full control over mesh parameters and supports both surface and volume meshing.

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

Control overall mesh density:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    min_mesh_size=0.5,   # Minimum element size
    max_mesh_size=10.0,  # Maximum element size
)
```

Smaller values = finer mesh = more triangles = slower transport but more accurate geometry.

## Surface Mesh Algorithms

`mesh_algorithm` sets GMSH's `Mesh.Algorithm`, which controls **2D surface
meshing**, not the tetrahedral volume mesh. GMSH provides multiple surface
meshing algorithms:

<!--pytest-codeblocks:skip-->
```python
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    mesh_algorithm=6,  # Frontal-Delaunay
)
```

**Available algorithms:**

| Algorithm | Name | Notes |
|-----------|------|-------|
| 1 | MeshAdapt | Default, adaptive |
| 2 | Automatic | GMSH chooses |
| 5 | Delaunay | Classic Delaunay |
| 6 | Frontal-Delaunay | Good for most cases |
| 7 | BAMG | Anisotropic |
| 8 | Frontal-Delaunay for Quads | Quad elements |
| 9 | Packing of Parallelograms | Structured regions |

See [GMSH mesh options](https://gmsh.info/doc/texinfo/gmsh.html#Mesh-options) for details.

## Per-Volume Mesh Sizing

Control mesh density per volume:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

coarse_box = cq.Workplane().box(1, 1, 2)
fine_box = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
default_box = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(coarse_box, name="coarse")
assembly.add(fine_box, name="fine")
assembly.add(default_box, name="global")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags="assembly_names")

model.export_dagmc_h5m_file(
    filename="different_resolution_meshes.h5m",
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,  # By material tag name
        "fine": 0.1,
        # "global" uses min/max only
    },
)
```

See [Mesh Sizing](mesh_sizing.md) for more details.

## CAD Transfer Method

Control how geometry is transferred to GMSH:

<!--pytest-codeblocks:skip-->
```python
# File method (default) - more compatible
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    method="file",  # Write temp BREP file
)

# In-memory method - faster for large geometries
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    method="in memory",  # Direct transfer
)
```

| Method | Pros | Cons |
|--------|------|------|
| `"file"` | More compatible, works with pip install | Slower (file I/O) |
| `"in memory"` | Faster for large geometries | Requires matching OCC versions |

## Advanced GMSH Options

For fine-grained control, access GMSH directly:

<!--pytest-codeblocks:skip-->
```python
import gmsh
import cad_to_dagmc

# Initialize GMSH
gmsh_obj = cad_to_dagmc.init_gmsh()

# ... add geometry and configure mesh ...

# Set advanced GMSH options
gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)
gmsh.option.setNumber("Mesh.Smoothing", 5)
gmsh.option.setNumber("Mesh.Algorithm", 6)

# Generate mesh
gmsh.model.mesh.generate(2)

# Export
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc.h5m")

gmsh.finalize()
```

## Volume Meshing

The GMSH backend writes tetrahedral volume meshes. The
[cad-to-dagmc-mesher backend](cad_to_dagmc_mesher_backend.md) does too, the
CadQuery backend does not:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10))

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

# Volume mesh for unstructured mesh tallies
model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    min_mesh_size=1.0,
    max_mesh_size=5.0,
)
```

### 3D Algorithms and Volume-Only Options

Use `mesh_algorithm_3d` to set `Mesh.Algorithm3D` independently of the surface
algorithm. The default is `1` (Delaunay); `10` selects HXT, which supports
multithreaded volume meshing. The `threads` argument controls GMSH's thread
count. Performance depends on the geometry, settings and GMSH build.

For finer control, `volume_mesh_options` accepts a dictionary mapping GMSH
option names to numeric or string values. Non-empty dictionaries cause the
surfaces to be meshed first, using `min_mesh_size`, `max_mesh_size` and
`set_size`. The overrides are then applied immediately before volume meshing,
so relaxing the interior sizing does not coarsen the existing surface mesh.

For example, to use HXT with relaxed interior sizing and standard quality
optimisation disabled:

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

These settings allow a coarser interior; they do not guarantee that all interior
refinement is disabled. Check the resulting mesh quality and resolution for
your application. Other GMSH size constraints still apply, including
`Mesh.MeshSizeMin` unless it is also overridden.

Both arguments are available on all three GMSH volume-export paths:

- `export_unstructured_mesh_file(...)`
- `export_gmsh_mesh_file(dimensions=3, ...)`
- `export_dagmc_h5m_file(unstructured_volumes=..., ...)`

The combined DAGMC/VTK export reuses the surface mesh already generated for the
DAGMC file. Surface-only exports do not apply `volume_mesh_options`. The
dictionary applies to the entire volume-meshing step, not to individual
volumes, and its values take precedence over corresponding named arguments
(including `mesh_algorithm_3d`) during that step. String values use
`gmsh.option.setString`; numeric values use `gmsh.option.setNumber`. GMSH
reports unsupported names or values as errors.

With `volume_mesh_options=None` or `{}`, the existing meshing sequence is
unchanged: direct volume exports use a single `generate(3)` call, while the
combined DAGMC/VTK export keeps its existing `generate(2)` then `generate(3)`
sequence. Options are scoped to the export's GMSH session and do not carry
over to subsequent exports. These controls do not apply to the CadQuery or
cad-to-dagmc-mesher backends.

## Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_mesh_size` | float | None | Minimum mesh element size |
| `max_mesh_size` | float | None | Maximum mesh element size |
| `mesh_algorithm` | int | 1 | GMSH 2D surface meshing algorithm |
| `mesh_algorithm_3d` | int | 1 | GMSH 3D volume algorithm: 1 = Delaunay, 10 = HXT |
| `volume_mesh_options` | dict | None | Numeric/string GMSH options applied after surface meshing, before volume meshing |
| `set_size` | dict | None | Per-volume mesh sizes |
| `method` | str | "file" | CAD transfer method |

## See Also

- [Mesh Sizing](mesh_sizing.md) - Per-volume mesh control
- [CadQuery Backend](cadquery_backend.md) - Alternative meshing backend
- [cad-to-dagmc-mesher Backend](cad_to_dagmc_mesher_backend.md) - Surface and volume meshing without GMSH
- [Parallel Processing](../advanced/parallel_processing.md) - Thread control
