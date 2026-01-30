# Meshing Backends

cad_to_dagmc supports two meshing backends: GMSH and CadQuery.

## GMSH Backend (Default)

The GMSH backend provides full control over mesh parameters and supports both
surface and volume meshing.

<!--pytest-codeblocks:skip-->
```python
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="gmsh",  # Default
    min_mesh_size=0.5,
    max_mesh_size=10.0,
    mesh_algorithm=1,
)
```

**Advantages:**

- Full control over mesh sizing
- Per-volume mesh sizing with `set_size`
- Multiple mesh algorithms available
- Supports volume meshing (unstructured mesh)
- Parallel meshing support

**Parameters:**

- `min_mesh_size`: Minimum mesh element size
- `max_mesh_size`: Maximum mesh element size
- `mesh_algorithm`: GMSH algorithm (1-10, default 1)
- `set_size`: Dict of volume IDs to target sizes

## CadQuery Backend

The CadQuery backend uses CadQuery's built-in tessellation for direct meshing.
This is simpler but provides less control.

<!--pytest-codeblocks:skip-->
```python
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="cadquery",
    tolerance=0.1,
    angular_tolerance=0.1,
)
```

**Advantages:**

- Often results in smaller meshesh with less triangle (particularly on flat surfaces)
- Simpler - no GMSH dependency for meshing
- Direct tessellation of CAD geometry
- Can be faster for simple geometries

**Limitations:**

- Cannot create volume meshes (no `export_unstructured_mesh_file`)
- Less control over mesh sizing
- `min_mesh_size`, `max_mesh_size`, `set_size` parameters are ignored

**Parameters:**

- `tolerance`: Linear tolerance for tessellation
- `angular_tolerance`: Angular tolerance for tessellation

:::{warning}
When using `meshing_backend="cadquery"`, the following parameters are ignored
and a warning is raised: `min_mesh_size`, `max_mesh_size`, `set_size`.
:::

## Comparison

| Feature | GMSH Backend | CadQuery Backend |
|---------|--------------|------------------|
| Surface mesh (h5m) | Yes | Yes |
| Volume mesh (vtk) | Yes | **No** |
| Mesh size control | Full (min/max/per-volume) | Limited (tolerance only) |
| Mesh algorithms | 10 algorithms | 1 (built-in) |
| Parallel meshing | Yes | Partly |
| Dependencies | Requires GMSH | Built into CadQuery |

## When to Use Each

**Use GMSH backend when:**

- You need volume meshes (unstructured mesh for tallies)
- You need precise control over mesh density
- You want per-volume mesh sizing
- You need parallel meshing for large models

**Use CadQuery backend when:**

- You only need surface meshes
- You want simpler configuration
- Your geometry is straightforward
- You want to avoid GMSH dependency
- You have flat surfaces in you geometry and want the smallest possible mesh for fastest particle transport.
