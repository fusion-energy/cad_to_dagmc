from cad_to_dagmc import CadToDagmc

my_model = CadToDagmc()
# the d and c from the word dagmc would be tagged with one material and the agm are tagged with another material
my_model.add_stp_file(
    "text_dagmc.stp", material_tags=["mat1", "mat2", "mat2", "mat2", "mat1"]
)
my_model.export_dagmc_h5m_file()
