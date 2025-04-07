import cad_to_dagmc
import cadquery as cq

result = sphere = cq.Workplane().moveTo(100, 0).sphere(5)

my_model =cad_to_dagmc.CadToDagmc()
my_model.add_cadquery_object(cadquery_object=result, material_tags=["mat1"])
my_model.export_gmsh_file_to_dagmc_h5m_file()
