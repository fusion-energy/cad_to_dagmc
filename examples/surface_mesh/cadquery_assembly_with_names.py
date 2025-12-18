# This example makes a CadQuery assembly and assigns names to the parts
# These part names are then used when exporting to a DAGMC H5M file
# This avoids needing to specify material tags separately when adding the CadQuery object


import cadquery as cq
from cad_to_dagmc import CadToDagmc

result = cq.Workplane().sphere(5)
result2 = cq.Workplane().moveTo(10, 0).sphere(2)

assembly = cq.Assembly()
assembly.add(result, name="result")
assembly.add(result2, name="result2")

my_model = CadToDagmc()
my_model.add_cadquery_object(cadquery_object=assembly, material_tags="assembly_names")
my_model.export_dagmc_h5m_file(min_mesh_size=0.5, max_mesh_size=1.0e6)
