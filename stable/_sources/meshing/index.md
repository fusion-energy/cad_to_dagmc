# Meshing Backends

cad_to_dagmc supports two meshing backends for creating surface meshes.

## Available Backends

| Backend | Description | Best For |
|---------|-------------|----------|
| [GMSH](gmsh_backend.md) | Full-featured meshing library | Complex models, volume meshes |
| [CadQuery](cadquery_backend.md) | Built-in CadQuery tessellation | Simple models, flat surfaces |

## Quick Comparison

| Feature | GMSH Backend | CadQuery Backend |
|---------|--------------|------------------|
| Surface mesh (h5m) | Yes | Yes |
| Volume mesh (vtk) | Yes | **No** |
| Mesh size control | Full (min/max/per-volume) | Limited (tolerance only) |
| Mesh algorithms | 10 algorithms | 1 (built-in) |
| Parallel meshing | Yes | Partial |
| Dependencies | Requires GMSH | Built into CadQuery |
| Flat surface efficiency | Standard | Better (fewer triangles) |

## Choosing a Backend

**Use GMSH backend (default) when:**
- You need volume meshes for unstructured mesh tallies
- You need precise control over mesh density
- You want per-volume mesh sizing with `set_size`
- You need parallel meshing for large models
- You need specific mesh algorithms

**Use CadQuery backend when:**
- You only need surface meshes
- You want simpler configuration
- Your geometry has many flat surfaces (fewer triangles)
- You want to minimize dependencies
- Your geometry is straightforward

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10))

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

# GMSH backend (default)
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
```

## Mesh Sizing Overview

For detailed per-volume mesh sizing, see [Mesh Sizing](mesh_sizing.md).
