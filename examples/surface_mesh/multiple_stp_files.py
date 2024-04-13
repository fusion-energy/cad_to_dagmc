from cad_to_dagmc import CadToDagmc
import cadquery as cq

result1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cq.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = cq.Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("two_connected_cubes.stp", exportType="STEP")

result = cq.Workplane().moveTo(100, 0).sphere(5)
assembly = cq.Assembly()
assembly.add(result)
assembly.save("single_sphere.stp", exportType="STEP")

my_model = CadToDagmc()
my_model.add_stp_file(
    filename="two_connected_cubes.stp",
    material_tags=["mat1", "mat2"],
)
my_model.add_stp_file(
    filename="single_sphere.stp",
    material_tags=["mat3"],
)

my_model.export_dagmc_h5m_file(
    max_mesh_size=1,
    min_mesh_size=0.5,
    implicit_complement_material_tag="air",
)
