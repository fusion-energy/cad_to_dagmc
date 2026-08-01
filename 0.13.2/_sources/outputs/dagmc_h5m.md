# DAGMC H5M Files

The primary output format. Creates triangular surface meshes for use with DAGMC-enabled transport codes (OpenMC, MCNP, FLUKA, etc.).

## Basic Export

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten"])

model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    min_mesh_size=0.5,
    max_mesh_size=10.0,
)
```

## With Different Backends

Choose between h5py (default) and pymoab backends:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

sphere1 = cq.Workplane().sphere(5)
sphere2 = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(sphere1)
assembly.add(sphere2)

model = CadToDagmc()
model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1", "mat2"])

# Export using h5py backend (default, no MOAB needed)
model.export_dagmc_h5m_file(
    filename="dagmc_h5py.h5m",
    h5m_backend="h5py",
)

# Export using pymoab backend (requires MOAB installation)
model.export_dagmc_h5m_file(
    filename="dagmc_pymoab.h5m",
    h5m_backend="pymoab",
)
```

## With Meshing Backends

Choose between the cad-to-dagmc-mesher (default), GMSH and CadQuery meshing:

<!--pytest-codeblocks:skip-->
```python
# cad-to-dagmc-mesher backend (default) - surface and volume meshing
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="cad-to-dagmc-mesher",
    tolerance=0.01,
    angular_tolerance=0.2,
)

# GMSH backend - full control over mesh parameters
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="gmsh",
    min_mesh_size=0.5,
    max_mesh_size=10.0,
    mesh_algorithm=1,
)

# CadQuery backend - simpler, uses CadQuery's tessellation
model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="cadquery",
    tolerance=0.1,
    angular_tolerance=0.1,
)
```

## API Reference

### `export_dagmc_h5m_file()`

**Common Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filename` | str | "dagmc.h5m" | Output file path |
| `scale_factor` | float | 1.0 | Geometry scale factor |
| `imprint` | bool or int | True | Imprint shared surfaces. An int limits the imprint to that many threads |
| `implicit_complement_material_tag` | str | None | Void space material tag |

**Backend Selection:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `meshing_backend` | str | auto | `"cad-to-dagmc-mesher"`, `"gmsh"` or `"cadquery"`. Auto-selected from the other arguments provided. Defaults to `"cad-to-dagmc-mesher"` when no backend-specific arguments are given, falling back to `"cadquery"` if cad-to-dagmc-mesher is not installed. |
| `h5m_backend` | str | "h5py" | `"h5py"` or `"pymoab"` for writing h5m files |

**GMSH Backend Parameters:**

These parameters only apply when using `meshing_backend="gmsh"` (or when auto-selected):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_mesh_size` | float | None | Minimum mesh element size |
| `max_mesh_size` | float | None | Maximum mesh element size |
| `mesh_algorithm` | int | 1 | GMSH meshing algorithm (1-10) |
| `method` | str | "file" | CAD transfer method: `"file"` or `"in memory"` |
| `set_size` | dict | None | Per-volume mesh sizes. Keys can be volume IDs (int) or material tag names (str). |
| `unstructured_volumes` | list | None | Volume IDs (int) or material tags (str) for conformal volume mesh |
| `umesh_filename` | str | "umesh.vtk" | Output filename for unstructured volume mesh |

**CadQuery Backend Parameters:**

These parameters only apply when using `meshing_backend="cadquery"`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tolerance` | float | 0.1 | Linear tolerance for tessellation |
| `angular_tolerance` | float | 0.1 | Angular tolerance for tessellation |

**cad-to-dagmc-mesher Backend Parameters:**

These parameters only apply when using `meshing_backend="cad-to-dagmc-mesher"`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tolerance` | float | 0.01 | Linear tolerance for the surface mesh |
| `angular_tolerance` | float | 0.2 | Angular tolerance for the surface mesh |
| `tet_volumes` | Iterable[str] | None | Material tag names of the volumes to fill with tetrahedra |
| `target_edge_length` | float | None | Target tetrahedron edge length |
| `umesh_filename` | str | "umesh.vtk" | Output filename for unstructured volume mesh |

`tet_volumes` and `target_edge_length` must be given together to write a volume mesh.

:::{warning}
Do not mix GMSH and CadQuery backend parameters in the same call. If you provide parameters from both backends without explicitly setting `meshing_backend`, an error will be raised.
:::

**Returns:**
- `str` - Path to the created h5m file
- Or `tuple[str, str]` - (h5m_path, vtk_path) when a volume mesh is also written, which is
  when `unstructured_volumes` is set on the GMSH backend, or when `tet_volumes` and
  `target_edge_length` are set on the cad-to-dagmc-mesher backend

## Using in OpenMC

Load the DAGMC geometry in OpenMC:

<!--pytest-codeblocks:skip-->
```python
import openmc

# Define materials (names must match material tags)
tungsten = openmc.Material(name="tungsten")
tungsten.add_element("W", 1.0)
tungsten.set_density("g/cm3", 19.3)

steel = openmc.Material(name="steel")
steel.add_element("Fe", 1.0)
steel.set_density("g/cm3", 7.8)

materials = openmc.Materials([tungsten, steel])

# Load the DAGMC geometry
dag_universe = openmc.DAGMCUniverse(filename="dagmc.h5m")
geometry = openmc.Geometry(root=dag_universe.bounded_universe())

# Set up settings
settings = openmc.Settings()
settings.batches = 10
settings.particles = 1000
settings.run_mode = "fixed source"

model = openmc.Model(geometry=geometry, materials=materials, settings=settings)
model.run()
```

## See Also

- [H5M Backends](../advanced/h5m_backends.md) - h5py vs pymoab comparison
- [GMSH Backend](../meshing/gmsh_backend.md) - GMSH meshing options
- [CadQuery Backend](../meshing/cadquery_backend.md) - CadQuery meshing options
- [Conformal Meshes](conformal_meshes.md) - Combined surface and volume output
