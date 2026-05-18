# Output Formats

cad_to_dagmc can create three types of output files for neutronics simulations.

## Output Types

| Format | Description | Use Case |
|--------|-------------|----------|
| [DAGMC H5M](dagmc_h5m.md) | Triangular surface mesh | Geometry for particle transport |
| [Unstructured VTK](unstructured_vtk.md) | Tetrahedral volume mesh | Mesh tallies in OpenMC |
| [GMSH Mesh](gmsh_mesh.md) | GMSH native format | Debugging, further processing |
| [Conformal Meshes](conformal_meshes.md) | Combined surface + volume | When you need both |

## Quick Comparison

| Feature | DAGMC H5M | Unstructured VTK | GMSH Mesh |
|---------|-----------|------------------|-----------|
| Surface mesh | Yes | No | Yes (2D) |
| Volume mesh | No | Yes | Yes (3D) |
| For geometry | Yes | No | Intermediate |
| For tallies | No | Yes | No |
| File extension | `.h5m` | `.vtk` | `.msh` |

## Basic Export Pattern

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# Create geometry
assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10), name="sphere")

# Initialize model
model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["tungsten"])

# Export to different formats
model.export_dagmc_h5m_file(filename="dagmc.h5m")           # Surface mesh
model.export_unstructured_mesh_file(filename="umesh.vtk")    # Volume mesh
model.export_gmsh_mesh_file(filename="mesh.msh")             # GMSH format
```

## Choosing an Output Format

**Use DAGMC H5M when:**
- Running DAGMC-enabled transport (OpenMC, MCNP, FLUKA)
- You need geometry definition for particle tracking
- Surface mesh is sufficient

**Use Unstructured VTK when:**
- Creating mesh tallies in OpenMC
- Need volumetric mesh for post-processing
- Doing CFD coupling

**Use GMSH Mesh when:**
- Debugging mesh quality
- Using GMSH visualization (Gmsh GUI)
- Further mesh processing needed

**Use Conformal Meshes when:**
- Running both transport and mesh tallies
- Surface and volume mesh boundaries must match exactly
