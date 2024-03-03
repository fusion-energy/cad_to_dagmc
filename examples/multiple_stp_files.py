from cad_to_dagmc import CadToDagmc

my_model = CadToDagmc()
my_model.add_stp_file("two_connected_cubes.stp")
my_model.add_stp_file("single_sphere.stp")

my_model.export_dagmc_h5m_file(
    max_mesh_size=1, min_mesh_size=0.5, implicit_complement_material_tag="air",
    material_tags=["mat1", "mat2", "mat3"]
)
