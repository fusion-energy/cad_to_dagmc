from cad_to_dagmc import CadToDagmc

my_model = CadToDagmc()
my_model.add_stp_file('examples/two_connected_cubes.stp', material_tags=['part1', 'part2'])
my_model.add_stp_file('examples/.stp', material_tags=['part1', 'part2'])
my_model.export_dagmc_h5m_file()
