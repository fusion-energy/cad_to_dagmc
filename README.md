A minimal package that uses CadQuery functionality to convert Cad geometry to DAGMC h5m files

This particular method of producing DAGMC compatible h5m files from CAD geometry
is intended to convert STP files or [CadQuery](https://cadquery.readthedocs.io) objects to h5m file.

The use of CadQuery based surface tesselation and then conversion of the
vertices and triangle sets into h5m files directly (in memory) is relatively
fast with minimal file IO and the resulting meshed volumes have low triangle
count while maintaining a good representation of the volume as described in
[this](https://www.sciencedirect.com/science/article/abs/pii/S0920379615301484)
publication.

While this package concentrates on loading the CAD and meshing the surface it
then hands off the vertices and triangles sets to
[vertices_to_h5m](https://github.com/fusion-energy/vertices_to_h5m) which
converts these into a h5m geometry file.
Due to the modularity of this workflow if you have a preferred meshing
algorithm then it is entirely possible to pipe your own vertices and triangles
directly into vertices_to_h5m.

# Install

```bash
pip install cad_to_dagmc
```

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