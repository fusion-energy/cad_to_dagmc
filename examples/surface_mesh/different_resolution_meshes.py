# This example makes 3 CAD boxes
# Meshes the 3 volumes with different resolutions
# exports the mesh to a DAGMC h5m file and GMsh msh file
import cadquery as cq
from cad_to_dagmc import CadToDagmc

box_set_size_course_mesh = cq.Workplane().box(1, 1, 2)
box_set_size_fine_mesh = cq.Workplane().moveTo(1, 0.5).box(1, 1, 1.5)
box_set_global_mesh = cq.Workplane().moveTo(2, 1).box(1, 1, 1)

assembly = cq.Assembly()
assembly.add(box_set_size_course_mesh, color=cq.Color(0, 0, 1), name="coarse")
assembly.add(box_set_size_fine_mesh, color=cq.Color(0, 1, 0), name="fine")
assembly.add(box_set_global_mesh, color=cq.Color(1, 0, 0), name="global")

assembly.export("different_resolution_meshes.step")

# uncomment to see the assembly in a pop up vtk viewer
# from cadquery import vis
# vis.show(assembly)

model = CadToDagmc()
# Use assembly names as material tags so we can reference them in set_size
model.add_cadquery_object(assembly, material_tags="assembly_names")

# You can see what material tags are available
print("Material tags:", model.material_tags)

# Use material tag names in set_size instead of volume IDs
model.export_dagmc_h5m_file(
    filename="different_resolution_meshes.h5m",
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,
        "fine": 0.1,
    },  # "global" is not specified so it uses only the min/max mesh sizes
)

model.export_gmsh_mesh_file(
    filename="different_resolution_meshes.msh",
    dimensions=2,
    min_mesh_size=0.01,
    max_mesh_size=10,
    set_size={
        "coarse": 0.9,
        "fine": 0.1,
    },  # "global" is not specified so it uses only the min/max mesh sizes
)
