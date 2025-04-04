# from cad_to_dagmc import MeshToDagmc
# import gmsh

# gmsh.initialize()
# mesh_file = gmsh.open('tests/tagged_mesh.msh')

# mesh = MeshToDagmc()
# mesh.export_gmsh_object_to_dagmc_h5m_file(gmsh_object=mesh_file)


import gmsh

gmsh.initialize()
mesh_file = gmsh.open('tests/tagged_mesh.msh')

# Get all 3D physical groups (volumes)
volume_groups = gmsh.model.getPhysicalGroups(3)
face_groups = gmsh.model.getPhysicalGroups(2)
print("Volume groups:", volume_groups)
gmsh.model.removePhysicalGroups(face_groups)
volume_groups = gmsh.model.getPhysicalGroups(3)
print("Volume groups:", volume_groups)

# # Get the name for each physical group
# for dim, tag in volume_groups:
#     name = gmsh.model.getPhysicalName(dim, tag)
#     print(f"Physical Group (dim={dim}, tag={tag}) has name: '{name}'")

# # You can also get all physical groups of all dimensions
# all_groups = gmsh.model.getPhysicalGroups()
# for dim, tag in all_groups:
#     name = gmsh.model.getPhysicalName(dim, tag)
#     print(f"Physical Group (dim={dim}, tag={tag}) has name: '{name}'")

# gmsh.finalize()