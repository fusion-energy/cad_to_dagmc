from cad_to_dagmc import CadToDagmc

my_model = CadToDagmc()
my_model.add_cadquery_solids()
my_model.export_dagmc_h5m_file()
