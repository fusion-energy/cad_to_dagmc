# GMSH Mesh Files

Export meshes in GMSH's native format for inspection, debugging, or further processing.

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

## With Per-Volume Mesh Sizing

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

model.export_gmsh_mesh_file(
    filename="different_resolution_meshes.msh",
    dimensions=2,
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,
        "fine": 0.1,
    },
)
```

## API Reference

### `export_gmsh_mesh_file()`

```python
model.export_gmsh_mesh_file(
    filename="mesh.msh",      # Output file path
    dimensions=2,             # 2 for surface, 3 for volume
    min_mesh_size=1.0,        # Minimum element size
    max_mesh_size=10.0,       # Maximum element size
    mesh_algorithm=1,         # GMSH algorithm (1-10)
    set_size=None,            # Per-volume sizes
    scale_factor=1.0,         # Geometry scaling
    imprint=True,             # Imprint shared surfaces
    method="file",            # CAD transfer method
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filename` | str | "mesh.msh" | Output GMSH file path |
| `dimensions` | int | 2 | Mesh dimensions (2=surface, 3=volume) |
| `min_mesh_size` | float | None | Minimum mesh element size |
| `max_mesh_size` | float | None | Maximum mesh element size |
| `mesh_algorithm` | int | 1 | GMSH meshing algorithm |
| `set_size` | dict | None | Per-volume mesh sizes |
| `scale_factor` | float | 1.0 | Geometry scale factor |
| `imprint` | bool | True | Imprint shared surfaces |
| `method` | str | "file" | CAD transfer method |

## Use Cases

### Debugging Mesh Quality

Export to GMSH format and open in the GMSH GUI:

```bash
gmsh mesh.msh
```

This allows you to:
- Visually inspect mesh quality
- Check element sizes
- Verify geometry import

### Creating Pre-meshed Files

Create a mesh file that can be converted to DAGMC later:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc
import cad_to_dagmc

# First, create GMSH mesh
result1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cq.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = cq.Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("geometry.stp", exportType="STEP")

geometry = CadToDagmc()
geometry.add_stp_file("geometry.stp")
geometry.export_gmsh_mesh_file(filename="mesh.msh")

# Later, convert to DAGMC
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    material_tags=["mat1", "mat2"],
    dagmc_filename="dagmc.h5m",
)
```

### 2D vs 3D Meshes

| Dimension | Mesh Type | Use Case |
|-----------|-----------|----------|
| `dimensions=2` | Triangular surface | DAGMC geometry input |
| `dimensions=3` | Tetrahedral volume | Volume mesh / analysis |

## See Also

- [GMSH Files Input](../inputs/gmsh_files.md) - Loading GMSH files back
- [GMSH Backend](../meshing/gmsh_backend.md) - Meshing parameters
- [GMSH Documentation](https://gmsh.info/doc/texinfo/gmsh.html) - Official GMSH docs
