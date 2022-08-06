import cad_to_dagmc
from vertices_to_h5m import vertices_to_h5m


# merged_cad_obj = cad_to_dagmc.load_stp_file("two_disconnected_cubes.stp")

# vertices, triangles = cad_to_dagmc.tessellate(merged_cad_obj, tolerance=2)


merged_cad_obj = cad_to_dagmc.load_stp_file("two_connected_cubes.stp")

vertices, triangles = cad_to_dagmc.tessellate(merged_cad_obj, tolerance=2)
