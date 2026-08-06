# Implicit Complement

Set a material tag for DAGMC's implicit complement - the void space outside/between your defined volumes.

## What is the Implicit Complement?

In DAGMC, the implicit complement is the region of space not occupied by any explicitly defined volume. By default, particles entering this region are "lost" (void). Setting an implicit complement material tag allows you to:

- Track particles in the void space
- Assign a material (like air) to the surrounding environment
- Score tallies in regions between components

## Basic Usage

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create some boxes (with void space between them)
box1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
box2 = cq.Workplane("XY").moveTo(20, 0).box(10.0, 10.0, 5.0)

assembly = cq.Assembly()
assembly.add(box1)
assembly.add(box2)

model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1", "mat2"])

model.export_dagmc_h5m_file(
    max_mesh_size=1,
    min_mesh_size=0.5,
    implicit_complement_material_tag="air",  # Tag the void as "air"
)
```

## Using in OpenMC

When using implicit complement in OpenMC, define a material with the matching name:

<!--pytest-codeblocks:skip-->
```python
import openmc

# Define the implicit complement material
air = openmc.Material(name="air")
air.add_element("N", 0.78)
air.add_element("O", 0.22)
air.set_density("g/cm3", 0.001225)

# Other materials...
mat1 = openmc.Material(name="mat1")
# ...

materials = openmc.Materials([air, mat1, ...])

# Load DAGMC geometry
universe = openmc.DAGMCUniverse("dagmc.h5m").bounded_universe()
geometry = openmc.Geometry(universe)
```

## With GMSH Files

Also works with GMSH file conversion:

<!--pytest-codeblocks:skip-->
```python
import cad_to_dagmc

cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m",
    material_tags=["mat1", "mat2"],
    implicit_complement_material_tag="void",
)
```

## Common Use Cases

| Material Tag | Use Case |
|--------------|----------|
| `"air"` | Atmospheric environment |
| `"void"` | Vacuum or placeholder |
| `"helium"` | Helium-cooled systems |
| `"water"` | Submerged components |

## When to Use

**Use implicit complement when:**
- You need to track particles in the void
- The surrounding medium affects particle transport
- You want tallies in the void region
- Components are separated and the space between matters

**Skip implicit complement when:**
- Void is truly vacuum (particle loss is acceptable)
- All space is filled by defined volumes
- You're only interested in the defined components

## See Also

- [DAGMC H5M Output](../outputs/dagmc_h5m.md) - Full export options
- [GMSH Files Input](../inputs/gmsh_files.md) - GMSH file conversion
