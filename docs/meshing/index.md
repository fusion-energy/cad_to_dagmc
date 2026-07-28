# Meshing Backends

cad_to_dagmc supports three meshing backends for creating surface and volume meshes.

## Available Backends

| Backend | Description | Best For |
|---------|-------------|----------|
| [GMSH](gmsh_backend.md) | Full-featured meshing library | Complex models, fine mesh control |
| [CadQuery](cadquery_backend.md) | Built-in CadQuery tessellation | Simple models, flat surfaces |
| [cad-to-dagmc-mesher](cad_to_dagmc_mesher_backend.md) | Purpose-built surface and tetrahedral mesher | Surface and volume meshes without GMSH |

## Quick Comparison

| Feature | GMSH | CadQuery | cad-to-dagmc-mesher |
|---------|------|----------|---------------------|
| Surface mesh (h5m) | Yes | Yes | Yes |
| Volume mesh (vtk) | Yes | **No** | Yes |
| Mesh size control | Full (min/max/per-volume) | Limited (tolerance only) | Tolerances + `target_edge_length` |
| Mesh algorithms | 10 algorithms | 1 (built-in) | 1 (built-in) |
| Parallel meshing | Yes | Partial | Yes (DAG scheduler) |
| Dependencies | Requires GMSH | Built into CadQuery | Installed with cad_to_dagmc |
| Flat surface efficiency | Standard | Better (fewer triangles) | Better (fewer triangles) |

## Choosing a Backend

**Use GMSH backend when:**
- You need precise control over mesh density
- You want per-volume mesh sizing with `set_size`
- You need parallel meshing for large models
- You need specific mesh algorithms

**Use CadQuery backend when:**
- You only need surface meshes
- You want simpler configuration
- Your geometry has many flat surfaces (fewer triangles)
- Your geometry is straightforward

**Use cad-to-dagmc-mesher backend (the default) when:**
- You need volume meshes for unstructured mesh tallies without GMSH
- You want the surface (h5m) and volume (vtk) meshes from a single meshing call
- You want simple configuration (tolerances plus one tetrahedron edge length)

A call that gives no backend and no backend-specific arguments uses
cad-to-dagmc-mesher. It is installed with the pip package but is not on
conda-forge, so a conda installation without it falls back to CadQuery.

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10))

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

# GMSH backend
model.export_dagmc_h5m_file(
    filename="dagmc_gmsh.h5m",
    meshing_backend="gmsh",
    min_mesh_size=0.5,
    max_mesh_size=10.0,
)

# CadQuery backend
model.export_dagmc_h5m_file(
    filename="dagmc_cq.h5m",
    meshing_backend="cadquery",
    tolerance=0.1,
    angular_tolerance=0.1,
)

# cad-to-dagmc-mesher backend
model.export_dagmc_h5m_file(
    filename="dagmc_mesher.h5m",
    meshing_backend="cad-to-dagmc-mesher",
    tolerance=0.01,
    angular_tolerance=0.2,
)
```

## Mesh Sizing Overview

For detailed per-volume mesh sizing, see [Mesh Sizing](mesh_sizing.md).
