import cadquery as cq
import cad_to_dagmc
import gmsh
import assembly_mesh_plugin

box_cutter = cq.Workplane("XY").moveTo(0, 5).box(20, 10, 20)
inner_sphere = cq.Workplane("XY").sphere(6).cut(box_cutter)
middle_sphere = cq.Workplane("XY").sphere(6.1).cut(box_cutter).cut(inner_sphere)
outer_sphere = cq.Workplane("XY").sphere(10).cut(box_cutter).cut(inner_sphere).cut(middle_sphere)
# outer_sphere=outer_sphere.cut(middle_sphere)

assembly = cq.Assembly()
assembly.add(inner_sphere, name="inner_sphere")
assembly.add(middle_sphere, name="middle_sphere")
# assembly.add(outer_sphere, name="outer_sphere")
# assembly.add(box_cutter, name="sec4ond_material")

# optionall show the geometry
# from cadquery.vis import show
# show(assembly)

# getTaggedGmsh initializes gmsh and creates a mesh object ready for meshing
assembly.getImprintedGmsh()
# Here you can set the mesh parameters

# Retrieve the volume associated with "inner_sphere"
inner_sphere_volume = gmsh.model.getEntitiesForPhysicalName("inner_sphere")  # 3 indicates volume
boundaries = gmsh.model.getBoundary([(3, inner_sphere_volume[0][1])], recursive=True)
gmsh.model.mesh.setSize(boundaries, 0.5)  # 0.5 is the small mesh size

middle_sphere_volume = gmsh.model.getEntitiesForPhysicalName("middle_sphere")  # 3 indicates volume
boundaries = gmsh.model.getBoundary([(3, middle_sphere_volume[0][1])], recursive=True)
gmsh.model.mesh.setSize(boundaries, 0.1)  # 0.5 is the small mesh size

# outer_sphere_volume = gmsh.model.getEntitiesForPhysicalName("outer_sphere")  # 3 indicates volume
# gmsh.model.mesh.setSize(gmsh.model.getBoundary([(3, outer_sphere_volume[0][1])], oriented=False), 0.5)  # 0.5 is the small mesh size


gmsh.model.mesh.generate(2)  # for DAGMC surface mesh we just need a 2D surface mesh

gmsh.write("assembly.msh")

# cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc_from_gmsh_object.h5m")

# finalize the GMSH API after using export_gmsh_object_to_dagmc_h5m_file
# and getTaggedGmsh as these both need access to the GMSH object.
gmsh.finalize()
