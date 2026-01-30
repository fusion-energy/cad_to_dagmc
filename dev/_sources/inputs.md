# Input Sources

cad_to_dagmc accepts geometry from three sources: CadQuery objects, STEP files, and GMSH files.

## CadQuery Objects

The most flexible option. Create geometry in Python using CadQuery and pass it directly.

```python
import cadquery as cq
import cad_to_dagmc

# Create geometry
part1 = cq.Workplane("XY").sphere(10)
part2 = cq.Workplane("XY").box(20, 20, 20).translate((30, 0, 0))

# Create an assembly
assembly = cq.Assembly()
assembly.add(part1)
assembly.add(part2)

# Add to model
my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags=["tungsten", "steel"]  # this cadquery object has two volumes
)
```

## STEP Files

Load geometry from STEP files. You can add single or multiple files.

**Single STEP file:**

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_stp_file(
    filename="geometry.step",
    material_tags=["mat1", "mat2"]  # this file has two volumes
)
```

**Multiple STEP files:**

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

my_model = cad_to_dagmc.CadToDagmc()
# each step file has a single volume
my_model.add_stp_file(filename="part1.step", material_tags=["tungsten"])
my_model.add_stp_file(filename="part2.step", material_tags=["steel"])
my_model.add_stp_file(filename="part3.step", material_tags=["water"])

my_model.export_dagmc_h5m_file(filename="combined.h5m")
```

## GMSH Files

Convert existing GMSH mesh files (.msh) to DAGMC h5m format.

**Using physical groups from the mesh:**

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

# Material tags are read from GMSH physical groups
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m"
)
```

**Specifying material tags manually:**

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m",
    material_tags=["mat1", "mat2"]
)
```

**From a GMSH object in memory:**

<!--pytest-codeblocks:skip-->
```python
import gmsh
import cad_to_dagmc

gmsh.initialize()
gmsh.open("mesh.msh")

cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(
    filename="dagmc.h5m"
)

gmsh.finalize()
```

## Using assembly-mesh-plugin

For CadQuery assemblies, you can use the [assembly-mesh-plugin](https://github.com/CadQuery/assembly-mesh-plugin)
to get a tagged GMSH mesh:

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
import assembly_mesh_plugin
import cad_to_dagmc

# Create assembly
box1 = cq.Workplane("XY").box(50, 50, 50)
box2 = cq.Workplane("XY").moveTo(0, 50).box(50, 50, 100)

assembly = cq.Assembly()
assembly.add(box1, name="steel")
assembly.add(box2, name="aluminum")

# Get tagged GMSH mesh (assembly names become physical groups)
mesh_object = assembly.getTaggedGmsh()
mesh_object.model.mesh.generate(2)

# Export to DAGMC (material tags from physical groups)
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc.h5m")

gmsh.finalize()
```
