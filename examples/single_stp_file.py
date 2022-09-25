from cad_to_dagmc import CadToDagmc

my_model = CadToDagmc()
my_model.add_stp_file("spline_extrude.stp", material_tags=["mat1"])
my_model.export_dagmc_h5m_file()
