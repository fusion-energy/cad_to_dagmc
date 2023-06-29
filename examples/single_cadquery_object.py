from cad_to_dagmc import CadToDagmc
import cadquery as cq

result = cq.Workplane().moveTo(100, 0).box(5,5,5)

my_model = CadToDagmc()
my_model.add_cadquery_object(result, material_tags=["mat1"])
my_model.export_dagmc_h5m_file()