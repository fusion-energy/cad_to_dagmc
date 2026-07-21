from cad_to_dagmc import CadToDagmc
import cadquery as cq

# This example writes a tetrahedral unstructured volume mesh using the
# cad-to-dagmc-mesher backend instead of gmsh. The resulting vtk file can be
# used with openmc.UnstructuredMesh(filename="umesh.vtk", library="moab").

result = cq.Workplane("XY").cylinder(height=10, radius=4)
result2 = cq.Workplane("XY").moveTo(0, 10).box(10, 10, 10)

my_model = CadToDagmc()

my_model.add_cadquery_object(result, material_tags=["mat1"])
my_model.add_cadquery_object(result2, material_tags=["mat2"])

# target_edge_length sets the tetrahedron size and also selects the
# cad-to-dagmc-mesher backend automatically
my_model.export_unstructured_mesh_file(
    filename="umesh_mesher.vtk",
    target_edge_length=2.0,
)

# the same backend can write the DAGMC h5m file and the volume mesh vtk file
# from a single meshing call, tet_volumes selects the volumes by material tag
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    tet_volumes=["mat1"],
    target_edge_length=2.0,
    umesh_filename="umesh_mat1.vtk",
)
