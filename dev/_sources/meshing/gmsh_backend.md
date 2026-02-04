# GMSH Backend

The GMSH backend (default) provides full control over mesh parameters and supports both surface and volume meshing.

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
    meshing_backend="gmsh",  # Default
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

## Mesh Algorithms

GMSH provides multiple meshing algorithms:

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
    method="inMemory",  # Direct transfer
)
```

| Method | Pros | Cons |
|--------|------|------|
| `"file"` | More compatible, works with pip install | Slower (file I/O) |
| `"inMemory"` | Faster for large geometries | Requires matching OCC versions |

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

Only GMSH backend supports volume meshes:

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

## Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_mesh_size` | float | None | Minimum mesh element size |
| `max_mesh_size` | float | None | Maximum mesh element size |
| `mesh_algorithm` | int | 1 | GMSH meshing algorithm |
| `set_size` | dict | None | Per-volume mesh sizes |
| `method` | str | "file" | CAD transfer method |

## See Also

- [Mesh Sizing](mesh_sizing.md) - Per-volume mesh control
- [CadQuery Backend](cadquery_backend.md) - Alternative meshing backend
- [Parallel Processing](../advanced/parallel_processing.md) - Thread control
