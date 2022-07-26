# cad_to_dagmc
A minimal package that uses CadQuery functionality to convert Cad geometry to DAGMC h5m files

# Usage

```python
import cad_to_dagmc

mat_tags=["mat1", "mat2"]
stp_file = cad_to_dagmc.load_stp_file("tests/two_connected_cubes.stp")
merged_stp_file = cad_to_dagmc.merge_surfaces(stp_file)
vertices, triangles = cad_to_dagmc.tessellate_parts(merged_stp_file, tolerance=2)

vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=mat_tags,
    h5m_filename="test.h5m",
)

transport_particles_on_h5m_geometry(
    h5m_filename="test.h5m", material_tags=mat_tags
)
```

```python
import cad_to_dagmc
import json
mat_tags=["mat1", "mat2", "mat3", "mat4", "mat5", "mat6"]
stp_file = cad_to_dagmc.load_stp_file("tests/multi_volume_cylinders.stp")
merged_stp_file = cad_to_dagmc.merge_surfaces(stp_file)
vertices, triangles = cad_to_dagmc.tessellate_parts(merged_stp_file, tolerance=2)

vertices_to_h5m(
    vertices=vertices,
    triangles=[triangles[0]],
    material_tags=mat_tags,
    h5m_filename="test.h5m",
)

transport_particles_on_h5m_geometry(
    h5m_filename="test.h5m", material_tags=mat_tags
)
````