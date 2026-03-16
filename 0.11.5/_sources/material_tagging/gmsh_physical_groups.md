# GMSH Physical Groups

When importing from GMSH mesh files, physical group names become material tags automatically.

## How It Works

GMSH physical groups are named collections of mesh entities. For DAGMC, 3D volume physical groups are used as material tags:

1. GMSH mesh has physical groups: `"shell"`, `"insert"`
2. Conversion extracts these names
3. DAGMC volumes get tagged: `mat:shell`, `mat:insert`

## Basic Usage

If your GMSH file already has physical groups:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

# Physical groups become material tags automatically
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh_with_physical_groups.msh",
    dagmc_filename="dagmc.h5m",
    # No material_tags needed!
)
```

## Complete Example with OpenMC

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc
import openmc

# Convert GMSH file - physical groups become material tags
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="tagged_mesh.msh",
    dagmc_filename="dagmc.h5m",
)

# Material names must match physical group names
mat1 = openmc.Material(name="shell")  # Matches physical group
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)

mat2 = openmc.Material(name="insert")  # Matches physical group
mat2.add_nuclide("H1", 1, percent_type="ao")
mat2.set_density("g/cm3", 0.002)

materials = openmc.Materials([mat1, mat2])

universe = openmc.DAGMCUniverse("dagmc.h5m").bounded_universe()
geometry = openmc.Geometry(universe)

settings = openmc.Settings()
settings.batches = 10
settings.particles = 500
settings.run_mode = "fixed source"

model = openmc.Model(geometry=geometry, materials=materials, settings=settings)
model.run()
```

## Using assembly-mesh-plugin

The [assembly-mesh-plugin](https://github.com/CadQuery/assembly-mesh-plugin) creates physical groups from CadQuery assembly names:

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
assembly.add(box1, name="first_material")   # Becomes physical group
assembly.add(box2, name="second_material")  # Becomes physical group

# getTaggedGmsh creates mesh with physical groups from names
assembly.getTaggedGmsh()

gmsh.option.setNumber("Mesh.MeshSizeMax", 4.2)
gmsh.model.mesh.generate(2)

# Export - physical groups become material tags
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(
    filename="dagmc.h5m"
)

gmsh.finalize()
```

## Overriding Physical Groups

You can override physical groups with manual tags:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

# Override physical groups with custom tags
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m",
    material_tags=["new_tag1", "new_tag2"],  # Overrides physical groups
)
```

## Creating Physical Groups in GMSH

If you're creating GMSH files manually:

<!--pytest-codeblocks:skip-->
```python
import gmsh

gmsh.initialize()

# Create geometry
gmsh.model.occ.addSphere(0, 0, 0, 1, tag=1)
gmsh.model.occ.addBox(-2, -2, -2, 4, 4, 4, tag=2)
gmsh.model.occ.cut([(3, 2)], [(3, 1)], tag=3)
gmsh.model.occ.synchronize()

# Create physical groups (3D = dimension 3)
gmsh.model.addPhysicalGroup(3, [1], name="sphere_material")
gmsh.model.addPhysicalGroup(3, [3], name="box_material")

gmsh.model.mesh.generate(2)
gmsh.write("mesh_with_groups.msh")
gmsh.finalize()
```

## Checking Physical Groups

To inspect physical groups in a GMSH file:

<!--pytest-codeblocks:skip-->
```python
import gmsh

gmsh.initialize()
gmsh.open("mesh.msh")

# Get 3D physical groups (dimension 3)
groups = gmsh.model.getPhysicalGroups(dim=3)
for dim, tag in groups:
    name = gmsh.model.getPhysicalName(dim, tag)
    print(f"Physical group {tag}: {name}")

gmsh.finalize()
```

## Requirements

For physical groups to work as material tags:
- Groups must be 3D (volume groups, dimension 3)
- Each volume should belong to exactly one physical group
- Group names should be valid material identifiers

## See Also

- [GMSH Files Input](../inputs/gmsh_files.md) - Loading GMSH files
- [GMSH Backend](../meshing/gmsh_backend.md) - Creating meshes with GMSH
- [GMSH Documentation](https://gmsh.info/doc/texinfo/gmsh.html#Physical-groups) - Official GMSH physical groups docs
