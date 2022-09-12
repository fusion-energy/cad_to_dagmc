from vertices_to_h5m import vertices_to_h5m
import cad_to_dagmc
import os

stp_files = [
    "tests/single_volume_thin.stp",
]
h5m_files = [
    "single_volume_thin.h5m",
]

for stp_file, h5m_file in zip(stp_files, h5m_files):

    merged_cad_obj = cad_to_dagmc.load_stp_file(stp_file)

    # merged_stp_file = cad_to_dagmc.merge_surfaces(stp_file)
    vertices, triangles = cad_to_dagmc.tessellate(merged_cad_obj, tolerance=0.0002)

    vertices_to_h5m(
        vertices=vertices,
        triangles=triangles,
        material_tags=["mat1"],
        h5m_filename=h5m_file,
    )
