import cadquery as cq
from cadquery import Assembly
from cad_to_dagmc import CadToDagmc

result = sphere = cq.Workplane().moveTo(100, 0).sphere(5)

assembly = Assembly(name="my assembly")
assembly.add(result)
assembly.save("examples/single_sphere.stp", exportType="STEP")


my_model = CadToDagmc()
my_model.add_stp_file("examples/single_sphere.stp", material_tags=["mat1"])
my_model.export_dagmc_h5m_file()
