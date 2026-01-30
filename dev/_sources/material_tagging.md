# Material Tagging

Material tags identify each volume in the DAGMC geometry. There are several ways to assign them.

## Manual Material Tags

The most explicit method - provide a list of material names matching the order of volumes.

```python
import cadquery as cq
import cad_to_dagmc

sphere = cq.Workplane("XY").sphere(10)
box = cq.Workplane("XY").box(20, 20, 20).translate((30, 0, 0))

assembly = cq.Assembly()
assembly.add(sphere)
assembly.add(box)

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags=["tungsten", "steel"]  # Order matters!
)
```

The first material tag is assigned to the first volume, second to second, etc.

## Using Assembly Names

Use the `name` parameter from CadQuery assemblies as material tags.

```python
import cadquery as cq
import cad_to_dagmc

sphere = cq.Workplane("XY").sphere(10)
box = cq.Workplane("XY").box(20, 20, 20).translate((30, 0, 0))

assembly = cq.Assembly()
assembly.add(sphere, name="tungsten")  # Name becomes material tag
assembly.add(box, name="steel")        # Name becomes material tag

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_names"  # Use names as tags
)
```

:::{note}
Parts without names will get auto-generated UUIDs as material tags.
:::

## Using Assembly Materials (CadQuery > 2.6.1)

CadQuery 2.6.1+ supports `cq.Material` objects. Use these as material tags.

<!--pytest-codeblocks:skip-->
```python
import cadquery as cq
import cad_to_dagmc

sphere = cq.Workplane("XY").sphere(10)
box = cq.Workplane("XY").box(20, 20, 20).translate((30, 0, 0))

assembly = cq.Assembly()
assembly.add(sphere, name="sphere", material=cq.Material("tungsten"))
assembly.add(box, name="box", material=cq.Material("steel"))

my_model = cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_materials"  # Use Material objects as tags
)
```

:::{warning}
This feature requires CadQuery > 2.6.1. All parts must have materials assigned,
or a `ValueError` will be raised.
:::

## GMSH Physical Groups

When importing from GMSH files, physical group names become material tags.

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

# Physical groups in the .msh file become material tags
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh_with_physical_groups.msh",
    dagmc_filename="dagmc.h5m"
)
```

You can also override physical groups with manual tags:

<!--pytest-codeblocks:skip-->
```python
cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m",
    material_tags=["mat1", "mat2"]  # Override physical groups
)
```

## Material Tag Format in H5M Files

Material tags are stored in the h5m file with a `mat:` prefix:

- `"tungsten"` becomes `"mat:tungsten"`
- `"steel"` becomes `"mat:steel"`

When using the geometry in OpenMC, reference materials without the prefix:

<!--pytest-codeblocks:skip-->
```python
import openmc

tungsten = openmc.Material(name="tungsten")
# ... define material properties
```
