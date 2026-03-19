# CadQuery Backend

The CadQuery backend uses CadQuery's built-in tessellation for direct meshing. This is simpler but provides less control than GMSH.

## Basic Usage

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10))

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="cadquery",
    tolerance=0.1,
    angular_tolerance=0.1,
)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tolerance` | float | 0.1 | Linear tolerance for tessellation |
| `angular_tolerance` | float | 0.1 | Angular tolerance for tessellation |

**Tolerance explanation:**
- Lower tolerance = finer mesh = more triangles
- `tolerance` controls how far the mesh can deviate from the true surface (linear distance)
- `angular_tolerance` controls the maximum angle between adjacent facet normals

## Advantages

| Advantage | Explanation |
|-----------|-------------|
| Fewer triangles on flat surfaces | CadQuery's tessellation optimizes flat regions |
| Simpler | Only 2 parameters to tune |
| No GMSH dependency | Uses built-in CadQuery tessellation |
| Can be faster | For simple geometries with flat surfaces |

## Limitations

| Limitation | Impact |
|------------|--------|
| No volume meshing | Cannot use `export_unstructured_mesh_file()` |
| No per-volume sizing | `set_size` parameter is ignored |
| No mesh algorithms | Only one tessellation method |
| Less control | Only tolerance parameters available |

:::{warning}
When using `meshing_backend="cadquery"`, the following parameters are **ignored** and a warning is raised:
- `min_mesh_size`
- `max_mesh_size`
- `set_size`
- `mesh_algorithm`
:::

## When to Use CadQuery Backend

**Good for:**
- Simple geometries
- Models with many flat surfaces (boxes, plates)
- When you want the smallest possible mesh
- Surface mesh only (no volume mesh needed)
- Minimizing dependencies

**Not suitable for:**
- When you need volume meshes
- When you need per-volume mesh sizing
- Complex curved geometries requiring fine control

## Comparison Example

The same geometry can produce different mesh sizes:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create a simple box (lots of flat surfaces)
box = cq.Workplane("XY").box(10, 10, 10)
assembly = cq.Assembly()
assembly.add(box)

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

# GMSH backend - may produce more triangles on flat surfaces
model.export_dagmc_h5m_file(
    filename="dagmc_gmsh.h5m",
    meshing_backend="gmsh",
    min_mesh_size=1.0,
    max_mesh_size=5.0,
)

# CadQuery backend - optimizes flat surfaces
model.export_dagmc_h5m_file(
    filename="dagmc_cq.h5m",
    meshing_backend="cadquery",
    tolerance=0.5,
)
```

For a simple box, CadQuery will use just 12 triangles (2 per face), while GMSH may create more based on the mesh size parameters.

## See Also

- [GMSH Backend](gmsh_backend.md) - Full-featured meshing backend
- [Mesh Sizing](mesh_sizing.md) - Per-volume mesh control (GMSH only)
