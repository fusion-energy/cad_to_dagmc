import cad_to_dagmc
import json
from .test_package import transport_particles_on_h5m_geometry
from vertices_to_h5m import vertices_to_h5m

mat_tags = ["mat1", "mat2"]
stp_file = cad_to_dagmc.load_stp_file("tests/two_connected_cubes.stp")

merged_stp_file = cad_to_dagmc.merge_surfaces(stp_file)
vertices, triangles = cad_to_dagmc.tessellate_touching_parts(
    merged_stp_file, tolerance=2
)

with open("data.json", "w") as f:
    json.dump([vertices, triangles], f, indent=1)

vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=mat_tags,
    h5m_filename="test.h5m",
)

transport_particles_on_h5m_geometry(h5m_filename="test.h5m", material_tags=mat_tags)


# mat_tags=["mat1", "mat2", "mat3", "mat4", "mat5", "mat6"]
# stp_file = cad_to_dagmc.load_stp_file("tests/multi_volume_cylinders.stp")