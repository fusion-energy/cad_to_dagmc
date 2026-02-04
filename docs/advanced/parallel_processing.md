# Parallel Processing

Both CadQuery and GMSH use parallel processing for operations like imprinting and meshing. By default, they use all available CPU cores.

## When to Limit Threads

- **Shared servers**: Avoid monopolizing all cores
- **Memory constraints**: Each thread requires memory; fewer threads = lower peak memory
- **Debugging**: Single-threaded execution can make errors easier to diagnose

## Limiting CadQuery Threads

CadQuery provides a `setThreads` function:

<!--pytest-codeblocks:skip-->
```python
from cadquery.occ_impl.shapes import setThreads

setThreads(4)  # Limit to 4 threads

# Now run your geometry operations
import cadquery as cq
from cad_to_dagmc import CadToDagmc

# ...
```

### Alternative: Configure Before Import

<!--pytest-codeblocks:skip-->
```python
import OCP
OCP.OSD.OSD_ThreadPool.DefaultPool_s(4)  # Limit to 4 threads

import cadquery as cq
from cad_to_dagmc import CadToDagmc

# ...
```

### Alternative: Environment Variable

```bash
export OMP_NUM_THREADS=4
python my_script.py
```

Or in Python:

<!--pytest-codeblocks:skip-->
```python
import os
os.environ["OMP_NUM_THREADS"] = "4"

import cadquery as cq
from cad_to_dagmc import CadToDagmc

# ...
```

## Limiting GMSH Threads

GMSH parallelism is controlled through its own options:

<!--pytest-codeblocks:skip-->
```python
import gmsh
import cad_to_dagmc

gmsh_obj = cad_to_dagmc.init_gmsh()

# Limit parallel meshing to 4 threads
gmsh.option.setNumber("General.NumThreads", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads1D", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads2D", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads3D", 4)

# ... continue with meshing ...
```

## Thread Options Summary

| Component | Method | When Applied |
|-----------|--------|--------------|
| CadQuery | `setThreads()` | Any time before operations |
| CadQuery | `OSD_ThreadPool.DefaultPool_s()` | Before importing CadQuery |
| CadQuery | `OMP_NUM_THREADS` env var | Before Python starts |
| GMSH | `General.NumThreads` | After GMSH initialization |
| GMSH | `Mesh.MaxNumThreads*D` | After GMSH initialization |

## Complete Example

<!--pytest-codeblocks:skip-->
```python
import os
os.environ["OMP_NUM_THREADS"] = "4"  # For CadQuery

import cadquery as cq
from cadquery.occ_impl.shapes import setThreads
import gmsh
import cad_to_dagmc

# Limit CadQuery threads
setThreads(4)

# Create geometry
assembly = cq.Assembly()
assembly.add(cq.Workplane("XY").sphere(10))

# Initialize model
model = cad_to_dagmc.CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1"])

# For advanced GMSH control
gmsh_obj = cad_to_dagmc.init_gmsh()
gmsh.option.setNumber("General.NumThreads", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads2D", 4)

# ... continue with export ...
```

## Performance Considerations

- More threads generally = faster for large models
- Memory usage scales with thread count
- On small models, threading overhead may negate benefits
- I/O bound operations don't benefit much from parallelism

## See Also

- [GMSH Backend](../meshing/gmsh_backend.md) - GMSH meshing options
- [Imprinting](imprinting.md) - Imprinting uses parallel processing
