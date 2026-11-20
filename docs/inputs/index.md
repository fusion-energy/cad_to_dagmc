# Input Sources

cad_to_dagmc accepts geometry from these sources:

| Input Type | Description | Use Case |
|------------|-------------|----------|
| [CadQuery Objects](cadquery_objects.md) | Python-defined geometry | Parametric models, scripted geometry |
| [CadQuery Assemblies](cadquery_assemblies.md) | Multi-part CadQuery assemblies | Tags taken from part names or materials |
| [STEP Files](step_files.md) | Industry-standard CAD exchange format | Importing from CAD software |
| [Gmsh Files](gmsh_files.md) | Existing Gmsh meshes, from a `.msh` file or the gmsh session | When you already have a mesh |

## Basic Pattern

CadQuery objects and STEP files follow the same pattern:

1. Create a `CadToDagmc` model.
2. Add geometry with `add_cadquery_object()` or `add_stp_file()`.
3. Export to one of the [output formats](../outputs/index.md).

```python
import cadquery as cq
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
model.add_cadquery_object(cq.Workplane().sphere(5), material_tags=["tungsten"])
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

`add_cadquery_object()` and `add_stp_file()` can be called several times and mixed. Volumes, and their material tags, keep the order they were added in; see [Multiple Objects](cadquery_objects.md#multiple-objects).

A Gmsh mesh does not go through `CadToDagmc`. A standalone function converts it to an h5m file, taking the tags from `material_tags` or from the mesh's physical groups; see [Gmsh Files](gmsh_files.md).

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import export_gmsh_file_to_dagmc_h5m_file

export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m",
)
```
