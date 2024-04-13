from cad_to_dagmc import CadToDagmc
import cadquery as cq

result = cq.Workplane("XY").moveTo(10, 0).box(3, 3, 0.5).edges("|Z").fillet(0.125)

result2 = cq.Workplane("XY").box(1.0, 1.0, 1.0)
assembly = cq.Assembly()
assembly.add(result2)
assembly.save("single_cube.stp", exportType="STEP")


my_model = CadToDagmc()

my_model.add_cadquery_object(
    cadquery_object=result,
    material_tags=["mat1"],
)

my_model.add_stp_file(
    filename="single_cube.stp",
    scale_factor=0.1,
    material_tags=["mat2"],
)

my_model.export_dagmc_h5m_file(
    max_mesh_size=0.2,
    min_mesh_size=0.1,
)
