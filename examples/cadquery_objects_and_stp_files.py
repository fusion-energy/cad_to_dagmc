from cad_to_dagmc import CadToDagmc
import cadquery as cq

text = cq.Workplane().text(txt="DAGMC", fontsize=10, distance=1)


my_model = CadToDagmc()
my_model.add_cadquery_object(
    object=text,
    material_tags=[
        "mat1",
        "mat2",
        "mat3",
        "mat4",
        "mat5",
    ],  # 5 volumes one for each letter
)

my_model.add_stp_file(
    filename="examples/two_connected_cubes.stp",
    material_tags=["mat1", "mat2"],  # two solids
    scale_factor=0.1,
)

print(my_model.parts)

my_model.export_dagmc_h5m_file(
    filename="cadquery_objects_and_stp_files.h5m",
    max_mesh_size=0.2,
    min_mesh_size=0.1
)
