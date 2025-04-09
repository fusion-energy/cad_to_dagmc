import cadquery as cq
import cad_to_dagmc
import gmsh
import assembly_mesh_plugin

box_shape1 = cq.Workplane("XY").box(50, 50, 50)
box_shape2 = cq.Workplane("XY").moveTo(0, 50).box(50, 50, 100)

assembly = cq.Assembly()
assembly.add(box_shape1, name="first_material")
assembly.add(box_shape2, name="second_material")

# getTaggedGmsh initializes gmsh and creates a mesh object ready for meshing
assembly.getTaggedGmsh()
# Here you can set the mesh parameters
# In this case, we set the minimum and maximum mesh size
# but you can set any other Gmsh parameters
# Remember that the gmsh has physical groups if you want to use them when meshing
gmsh.option.setNumber("Mesh.MeshSizeMax", 4.2)
gmsh.model.mesh.generate(2)  # for DAGMC surface mesh we just need a 2D surface mesh

cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc_from_gmsh_object.h5m")

# finalize the GMSH API after using export_gmsh_object_to_dagmc_h5m_file
# and getTaggedGmsh as these both need access to the GMSH object.
gmsh.finalize()
