from cad_to_dagmc import CadToDagmc

my_model = CadToDagmc()
my_model.add_stp_file(
    filename="two_connected_cubes.stp",
    material_tags=["mat1", "mat2"],
)
my_model.add_stp_file(
    filename="single_sphere.stp",
    material_tags=["mat3"],
)

my_model.export_dagmc_h5m_file(
    max_mesh_size=1,
    min_mesh_size=0.5,
    implicit_complement_material_tag="air",
)
