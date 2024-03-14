from cad_to_dagmc import CadToDagmc

my_model = CadToDagmc()
my_model.add_stp_file("spline_extrude.stp")
my_model.export_dagmc_h5m_file(material_tags=["mat1"])
