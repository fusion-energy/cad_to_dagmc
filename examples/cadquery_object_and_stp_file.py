from cad_to_dagmc import CadToDagmc
import cadquery as cq

result = cq.Workplane("XY").moveTo(10, 0).box(3, 3, 0.5).edges("|Z").fillet(0.125)

my_model = CadToDagmc()
my_model.add_cadquery_object(object=result, material_tags=["mat1"])
my_model.add_stp_file(
    filename="single_cube.stp", material_tags=["mat2"], scale_factor=0.1
)
my_model.export_dagmc_h5m_file(max_mesh_size=0.2, min_mesh_size=0.1)
