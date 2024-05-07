import gmsh

part = importers.importStep(str(filename)).val()

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.model.add("made_with_cad_to_dagmc_package")
volumes = gmsh.model.occ.importShapesNativePointer("two_connected_cubes.stp")
gmsh.model.occ.synchronize()

gmsh.option.setNumber("Mesh.Algorithm", 1)
gmsh.option.setNumber("Mesh.MeshSizeMin", 1)
gmsh.option.setNumber("Mesh.MeshSizeMax", 100)
gmsh.model.mesh.generate(2)

gmsh.write("mesh.msh")

gmsh.finalize()
