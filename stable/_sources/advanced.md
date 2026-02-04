# Advanced Options

This page covers advanced configuration options.

## Geometry Scaling

Scale geometry using the `scale_factor` parameter. Useful when converting
between units (e.g., mm to cm for neutronics).

<!--pytest-codeblocks:skip-->
```python
# Scale from mm to cm (divide by 10)
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    scale_factor=0.1,
)

# Scale up by 2x
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    scale_factor=2.0,
)
```

## Per-Volume Mesh Sizing

Set different mesh sizes for different volumes using `set_size`.

<!--pytest-codeblocks:skip-->
```python
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    min_mesh_size=1.0,
    max_mesh_size=10.0,
    set_size={
        1: 0.5,   # Volume 1: fine mesh (0.5)
        2: 5.0,   # Volume 2: coarse mesh (5.0)
        3: 1.0,   # Volume 3: medium mesh (1.0)
    }
)
```

:::{note}
`set_size` only works with the GMSH meshing backend.
:::

## Mesh Algorithms

GMSH provides multiple meshing algorithms. Select with `mesh_algorithm`.

<!--pytest-codeblocks:skip-->
```python
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    mesh_algorithm=6,  # Frontal-Delaunay
)
```

**Available algorithms:**

- `1`: MeshAdapt (default)
- `2`: Automatic
- `5`: Delaunay
- `6`: Frontal-Delaunay
- `7`: BAMG
- `8`: Frontal-Delaunay for Quads
- `9`: Packing of Parallelograms

See [GMSH documentation](https://gmsh.info/doc/texinfo/gmsh.html#Mesh-options)
for details.

## Imprinting Control

Imprinting ensures shared surfaces between adjacent volumes are meshed consistently.
It's enabled by default but can be disabled for geometries that don't need it.

<!--pytest-codeblocks:skip-->
```python
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    imprint=False,  # Disable imprinting
)
```

:::{warning}
Disabling imprinting may cause mesh inconsistencies at volume interfaces.
Only disable if you know your geometry doesn't require it.
:::

## CAD Transfer Method

Control how CAD geometry is transferred to GMSH.

<!--pytest-codeblocks:skip-->
```python
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    method="file",      # Write to temp file (default, more compatible)
    # or
    method="inMemory",  # Direct transfer (faster, requires matching OCC versions)
)
```

**File method (default):**

- More compatible across installations
- Works with pip-installed packages
- Slightly slower due to file I/O

**In-memory method:**

- Faster for large geometries
- Requires matching OpenCASCADE versions between CadQuery and GMSH
- Works reliably with Conda installations

## Implicit Complement Material

Set a material tag for DAGMC's implicit complement (the void space).

<!--pytest-codeblocks:skip-->
```python
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    implicit_complement_material_tag="void",
)
```

## Accessing the GMSH Object

For advanced mesh control, access the GMSH object directly.

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

# Generate mesh
gmsh.model.mesh.generate(2)

# Export
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc.h5m")

gmsh.finalize()
```

## Parallel Processing

Both CadQuery and GMSH use parallel processing for operations like imprinting and meshing.
By default, they use all available CPU cores. On shared servers or when memory is limited,
you may want to restrict the number of threads.

### Limiting CadQuery Threads

CadQuery provides a `setThreads` function to control the number of threads used for
boolean operations and imprinting:

<!--pytest-codeblocks:skip-->
```python
from cadquery.occ_impl.shapes import setThreads

setThreads(4)  # Limit to 4 threads
```

This can be called at any point before your geometry operations.

Alternatively, you can configure the thread pool before importing CadQuery:

<!--pytest-codeblocks:skip-->
```python
import OCP
OCP.OSD.OSD_ThreadPool.DefaultPool_s(4)  # Limit to 4 threads

import cadquery as cq
from cad_to_dagmc import CadToDagmc
```

Or use the `OMP_NUM_THREADS` environment variable:

<!--pytest-codeblocks:skip-->
```bash
export OMP_NUM_THREADS=4
python my_script.py
```

### Limiting GMSH Threads

GMSH parallelism is controlled through its own options:

<!--pytest-codeblocks:skip-->
```python
import gmsh
import cad_to_dagmc

gmsh_obj = cad_to_dagmc.init_gmsh()

# Limit parallel meshing to 4 threads
gmsh.option.setNumber("General.NumThreads", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads1D", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads2D", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads3D", 4)

# ... continue with meshing ...
```

### When to Limit Threads

- **Shared servers**: Avoid monopolizing all cores
- **Memory constraints**: Each thread requires memory; fewer threads = lower peak memory
- **Debugging**: Single-threaded execution can make errors easier to diagnose
