# Unstructured Mesh VTK Files

Creates tetrahedral volume meshes for use with OpenMC's `UnstructuredMesh` tally.

:::{note}
Volume mesh output **requires the GMSH backend**. The CadQuery meshing backend cannot create volume meshes.
:::

## Basic Export

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten"])

model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    min_mesh_size=1.0,
    max_mesh_size=5.0,
)
```

## Complex Geometry Example

Volume meshes work with complex curved geometries:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc
from math import sin, cos, pi, floor

def hypocycloid(t, r1, r2):
    return (
        (r1 - r2) * cos(t) + r2 * cos(r1 / r2 * t - t),
        (r1 - r2) * sin(t) + r2 * sin(-(r1 / r2 * t - t)),
    )

def epicycloid(t, r1, r2):
    return (
        (r1 + r2) * cos(t) - r2 * cos(r1 / r2 * t + t),
        (r1 + r2) * sin(t) - r2 * sin(r1 / r2 * t + t),
    )

def gear(t, r1=4, r2=1):
    if (-1) ** (1 + floor(t / 2 / pi * (r1 / r2))) < 0:
        return epicycloid(t, r1, r2)
    else:
        return hypocycloid(t, r1, r2)

# Create gear with twist
gear_shape = (
    cq.Workplane("XY")
    .parametricCurve(lambda t: gear(t * 2 * pi, 6, 1))
    .twistExtrude(15, 90)
    .faces(">Z")
    .workplane()
    .circle(2)
    .cutThruAll()
)

# Create spline extrusion
spline_points = [
    (2.75, 1.5), (2.5, 1.75), (2.0, 1.5),
    (1.5, 1.0), (1.0, 1.25), (0.5, 1.0), (0, 1.0),
]
s = cq.Workplane("XY")
r = s.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
spline_shape = r.extrude(-20)

model = CadToDagmc()
model.add_cadquery_object(gear_shape, material_tags=["mat1"])
model.add_cadquery_object(spline_shape, material_tags=["mat2"])

model.export_unstructured_mesh_file(
    filename="umesh.vtk",
    max_mesh_size=1,
    min_mesh_size=0.1,
)
```

## Selecting Specific Volumes

Export only certain volumes to the VTK file:

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="partial_mesh.vtk",
    volumes=[1, 3],  # Only include volumes 1 and 3
    min_mesh_size=1.0,
    max_mesh_size=5.0,
)
```

You can also use material tag names:

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="fuel_mesh.vtk",
    volumes=["fuel"],  # All volumes with "fuel" material tag
    min_mesh_size=0.5,
    max_mesh_size=2.0,
)
```

## API Reference

### `export_unstructured_mesh_file()`

<!--pytest-codeblocks:skip-->
```python
model.export_unstructured_mesh_file(
    filename="umesh.vtk",     # Output file path
    min_mesh_size=1.0,        # Minimum element size
    max_mesh_size=10.0,       # Maximum element size
    mesh_algorithm=1,         # GMSH algorithm (1-10)
    set_size=None,            # Per-volume sizes
    volumes=None,             # Specific volumes to include
    scale_factor=1.0,         # Geometry scaling
    imprint=True,             # Imprint shared surfaces
    method="file",            # CAD transfer method
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filename` | str | "umesh.vtk" | Output VTK file path |
| `min_mesh_size` | float | None | Minimum mesh element size |
| `max_mesh_size` | float | None | Maximum mesh element size |
| `mesh_algorithm` | int | 1 | GMSH meshing algorithm |
| `set_size` | dict | None | Per-volume mesh sizes |
| `volumes` | list | None | Specific volumes to mesh |
| `scale_factor` | float | 1.0 | Geometry scale factor |
| `imprint` | bool | True | Imprint shared surfaces |
| `method` | str | "file" | CAD transfer method |

## Using in OpenMC

Load the unstructured mesh for tallies:

<!--pytest-codeblocks:skip-->
```python
import openmc

# Create mesh from VTK file
mesh = openmc.UnstructuredMesh(filename="umesh.vtk", library="moab")

# Create tally with mesh filter
mesh_filter = openmc.MeshFilter(mesh)
tally = openmc.Tally()
tally.filters = [mesh_filter]
tally.scores = ["flux", "heating"]

tallies = openmc.Tallies([tally])
```

## Complete OpenMC Workflow

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc
import openmc

# Create geometry
sphere = cq.Workplane("XY").sphere(10)
assembly = cq.Assembly()
assembly.add(sphere, name="sphere")

# Export both surface and volume mesh
model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

model.export_dagmc_h5m_file(filename="dagmc.h5m")
model.export_unstructured_mesh_file(filename="umesh.vtk")

# Set up OpenMC
mat1 = openmc.Material(name="mat1")
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)
materials = openmc.Materials([mat1])

# Geometry from DAGMC
universe = openmc.DAGMCUniverse("dagmc.h5m").bounded_universe()
geometry = openmc.Geometry(universe)

# Unstructured mesh tally
umesh = openmc.UnstructuredMesh("umesh.vtk", library="moab")
mesh_filter = openmc.MeshFilter(umesh)
tally = openmc.Tally(name="mesh_tally")
tally.filters = [mesh_filter]
tally.scores = ["flux"]
tallies = openmc.Tallies([tally])

# Settings
settings = openmc.Settings()
settings.batches = 10
settings.particles = 5000
settings.run_mode = "fixed source"

# Run
model = openmc.Model(geometry, materials, settings, tallies)
model.run()
```

## See Also

- [Conformal Meshes](conformal_meshes.md) - When you need matching surface and volume meshes
- [Per-Volume Mesh Sizing](../meshing/mesh_sizing.md) - Control mesh density
- [GMSH Backend](../meshing/gmsh_backend.md) - Meshing options
