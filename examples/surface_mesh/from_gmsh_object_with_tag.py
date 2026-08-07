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
# Remember that the gmsh has physical groups if you want to use them when meshing
# Retrieve the volume associated with "first_material"
first_material_volume =   # 3 indicates volume

# Set a smaller mesh size for the "first_material" volume
for volume in gmsh.model.getEntitiesForPhysicalName(3, "first_material"):
    # The 3 indicates that we are looking for volume entities.
    gmsh.model.mesh.setSize(gmsh.model.getBoundary([(3, volume)], oriented=False), 0.5)  # 0.5 is the small mesh size

for volume in gmsh.model.getEntitiesForPhysicalName(3, "second_material"):
    gmsh.model.mesh.setSize(gmsh.model.getBoundary([(3, volume)], oriented=False), 1.5)  # 0.5 is the small mesh size

gmsh.model.mesh.generate(2)  # for DAGMC surface mesh we just need a 2D surface mesh

cad_to_dagmc.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc_from_gmsh_object.h5m")

# finalize the GMSH API after using export_gmsh_object_to_dagmc_h5m_file
# and getTaggedGmsh as these both need access to the GMSH object.
gmsh.finalize()
