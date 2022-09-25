import cadquery as cq
from cadquery import Assembly
from cad_to_dagmc import CadToDagmc

result = cq.Workplane().sphere(5)
result2 = sphere = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = Assembly()
assembly.add(result)
assembly.add(result2)

my_model = CadToDagmc()
my_model.add_cadquery_object(assembly, material_tags=["mat1", "mat2"])
my_model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0)
