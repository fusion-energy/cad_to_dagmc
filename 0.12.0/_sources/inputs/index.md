# Input Sources

cad_to_dagmc accepts geometry from three sources:

| Input Type | Description | Use Case |
|------------|-------------|----------|
| [CadQuery Objects](cadquery_objects.md) | Python-defined geometry | Parametric models, scripted geometry |
| [CadQuery Assemblies](cadquery_assemblies.md) | Multi-part CadQuery assemblies | Complex models with multiple components |
| [STEP Files](step_files.md) | Industry-standard CAD format can also contain assemblies | Importing from CAD software |
| [GMSH Files](gmsh_files.md) | Pre-existing mesh files | When you already have a mesh |

## Basic Pattern

All input methods follow the same pattern:

1. Create a `CadToDagmc` model
2. Add geometry using `add_cadquery_object()` or `add_stp_file()`
3. Export to desired format

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import CadToDagmc

model = CadToDagmc()
# Add geometry here...
model.export_dagmc_h5m_file(filename="dagmc.h5m")
```

For GMSH files, use the standalone function:

<!--pytest-codeblocks:skip-->
```python
from cad_to_dagmc import export_gmsh_file_to_dagmc_h5m_file

export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="mesh.msh",
    dagmc_filename="dagmc.h5m"
)
```
