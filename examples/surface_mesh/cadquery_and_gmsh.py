# This example shows how to create a DAGMC surface mesh from a CadQuery geometry
# The main point of this example is to highlight how the mesh can be fully
# performed within GMsh and then we can export the Gmsh object to a DAGMC h5m file
# using the cad_to_dagmc python package.
# This example is possible thanks to the assembly_mesh_plugin package which adds
# the getImprintedGmsh() method to the cq.Assembly class.

import cadquery as cq
import cad_to_dagmc
import gmsh
import assembly_mesh_plugin  # adds the getImprintedGmsh() method to cq.Assembly

box_cutter = cq.Workplane("XY").moveTo(0, 5).box(20, 10, 20)
inner_sphere = cq.Workplane("XY").sphere(6).cut(box_cutter)
middle_sphere = cq.Workplane("XY").sphere(6.1).cut(box_cutter).cut(inner_sphere)

assembly = cq.Assembly()
assembly.add(inner_sphere, name="inner_sphere")
assembly.add(middle_sphere, name="middle_sphere")

# optionally show the geometry
# from cadquery.vis import show
# show(assembly)

# getImprintedGmsh initializes gmsh and creates a mesh object ready for meshing
assembly.getImprintedGmsh()
# Here you can set the mesh parameters

# Retrieve the volume associated with "inner_sphere"
inner_sphere_volume = gmsh.model.getEntitiesForPhysicalName("inner_sphere")  # 3 indicates volume
boundaries = gmsh.model.getBoundary([(3, inner_sphere_volume[0][1])], recursive=True)
gmsh.model.mesh.setSize(boundaries, 0.5)  # 0.5 is the small mesh size

middle_sphere_volume = gmsh.model.getEntitiesForPhysicalName("middle_sphere")  # 3 indicates volume
boundaries = gmsh.model.getBoundary([(3, middle_sphere_volume[0][1])], recursive=True)
gmsh.model.mesh.setSize(boundaries, 0.1)  # 0.1 is the small mesh size


gmsh.model.mesh.generate(2)  # for DAGMC surface mesh we just need a 2D surface mesh

# material tags are found automatically as they are the names used for the
# 3d physical groups in the gmsh object which in turn come from the names
# used in the cadquery assembly. "inner_sphere" and "middle_sphere" in this case.
cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc_from_gmsh_object.h5m")

# finalize the GMSH API after using export_gmsh_object_to_dagmc_h5m_file
# and getImprintedGmsh as these both need access to the GMSH object.
gmsh.finalize()
