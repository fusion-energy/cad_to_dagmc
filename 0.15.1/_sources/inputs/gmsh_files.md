# GMSH Files

Convert existing GMSH mesh files (.msh) to DAGMC h5m format. This is useful when you already have a mesh or want to use GMSH's advanced meshing capabilities directly.

## From GMSH File with Manual Tags

Convert a GMSH mesh file and specify material tags:

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc
import cad_to_dagmc

# First, create a GMSH file (for this example)
result1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cq.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = cq.Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("two_connected_cubes.stp", exportType="STEP")

geometry = CadToDagmc()
geometry.add_stp_file("two_connected_cubes.stp")
geometry.export_gmsh_mesh_file(filename="example_gmsh_mesh.msh")

# Now convert the GMSH file to DAGMC
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="example_gmsh_mesh.msh",
    material_tags=["mat1", "mat2"],
    dagmc_filename="dagmc.h5m",
)
```

## From GMSH File with Physical Groups

If your GMSH file already has physical groups (3D volume groups), these are automatically used as material tags:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

# Material tags are read from GMSH physical groups
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh_with_physical_groups.msh",
    # No material_tags needed - uses physical groups
    dagmc_filename="dagmc.h5m",
)
```

:::{note}
When using physical groups, the group names become the material tags. Make sure your GMSH physical groups are named appropriately for your simulation.
:::

## Using assembly-mesh-plugin

The [assembly-mesh-plugin](https://github.com/CadQuery/assembly-mesh-plugin) provides a convenient way to create GMSH meshes from CadQuery assemblies with automatic physical group assignment:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
import cad_to_dagmc
import gmsh
import assembly_mesh_plugin

# Create assembly with named parts
box1 = cq.Workplane("XY").box(50, 50, 50)
box2 = cq.Workplane("XY").moveTo(0, 50).box(50, 50, 100)

assembly = cq.Assembly()
assembly.add(box1, name="first_material")   # Name becomes physical group
assembly.add(box2, name="second_material")  # Name becomes physical group

# getTaggedGmsh initializes gmsh and creates mesh with physical groups
assembly.getTaggedGmsh()

# Set mesh parameters
gmsh.option.setNumber("Mesh.MeshSizeMax", 4.2)
gmsh.model.mesh.generate(2)  # 2D surface mesh for DAGMC

# Export to DAGMC - physical groups become material tags
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(
    filename="dagmc_from_gmsh_object.h5m"
)

# Clean up GMSH
gmsh.finalize()
```

## From GMSH Object in Memory

If you have a GMSH object already initialized in memory:

<!--pytest-codeblocks:skip-->
```python
import gmsh
import cad_to_dagmc

# Initialize and set up GMSH
gmsh.initialize()
gmsh.open("mesh.msh")

# Export directly from the GMSH object
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(
    filename="dagmc.h5m",
    material_tags=["mat1", "mat2"],  # Optional: override physical groups
)

gmsh.finalize()
```

## Complete OpenMC Workflow

Here's a complete example from GMSH mesh to OpenMC simulation:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc
import openmc

# Convert GMSH file (with physical groups) to DAGMC
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="tagged_mesh.msh",
    dagmc_filename="dagmc.h5m",
)

# Set up OpenMC materials (names match physical groups)
mat1 = openmc.Material(name="shell")
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)

mat2 = openmc.Material(name="insert")
mat2.add_nuclide("H1", 1, percent_type="ao")
mat2.set_density("g/cm3", 0.002)

materials = openmc.Materials([mat1, mat2])

# Load DAGMC geometry
universe = openmc.DAGMCUniverse("dagmc.h5m").bounded_universe()
geometry = openmc.Geometry(universe)

# Configure and run
settings = openmc.Settings()
settings.batches = 10
settings.particles = 500
settings.run_mode = "fixed source"

model = openmc.Model(geometry=geometry, materials=materials, settings=settings)
model.run()
```

## API Reference

### `export_gmsh_file_to_dagmc_h5m_file()`

<!--pytest-codeblocks:skip-->
```python
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename,                        # Path to GMSH .msh file
    dagmc_filename="dagmc.h5m",           # Output DAGMC file
    material_tags=None,                   # Optional: override physical groups
    implicit_complement_material_tag=None,# Optional: void material tag
    h5m_backend="h5py",                   # "h5py" or "pymoab"
)
```

### `export_gmsh_object_to_dagmc_h5m_file()`

<!--pytest-codeblocks:skip-->
```python
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(
    filename="dagmc.h5m",                 # Output DAGMC file
    material_tags=None,                   # Optional: override physical groups
    implicit_complement_material_tag=None,# Optional: void material tag
    h5m_backend="h5py",                   # "h5py" or "pymoab"
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gmsh_filename` | str | Path to GMSH mesh file |
| `dagmc_filename` | str | Output DAGMC h5m file path |
| `filename` | str | Output DAGMC h5m file path (for object function) |
| `material_tags` | list[str] | Material tags (overrides physical groups if provided) |
| `implicit_complement_material_tag` | str | Material tag for void space |
| `h5m_backend` | str | "h5py" (default) or "pymoab" |

## See Also

- [GMSH Physical Groups](../material_tagging/gmsh_physical_groups.md) - Using physical groups as tags
- [GMSH Backend](../meshing/gmsh_backend.md) - Creating GMSH meshes from CAD
- [GMSH Documentation](https://gmsh.info/doc/texinfo/gmsh.html) - Official GMSH docs
