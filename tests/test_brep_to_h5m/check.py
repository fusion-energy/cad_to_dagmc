from cad_to_dagmc import CadToDagmc
import cadquery as cq
import OCP

result = cq.Workplane("front").box(2.0, 2.0, 0.5)

volumes = 1
material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

my_model = CadToDagmc()

my_model.add_cadquery_object(
    result,
    material_tags=["mat1"],
)


bldr = OCP.BOPAlgo.BOPAlgo_Splitter()
parts = [result]
if len(parts) == 1:
    # merged_solid = cq.Compound(solids)

    merged_surface_compound = parts[0].toOCC()
else:
    for solid in parts:
        # checks if solid is a compound as .val() is not needed for compounds
        if isinstance(solid, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            bldr.AddArgument(solid.wrapped)
        else:
            bldr.AddArgument(solid.val().wrapped)

    bldr.SetNonDestructive(True)

    bldr.Perform()

    bldr.Images()

    merged_surface_compound = cq.Compound(bldr.Shape()).wrapped
import gmsh

topods = merged_surface_compound
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
volumes = gmsh.model.occ.importShapesNativePointer(topods._address())
gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.Algorithm", 1)
gmsh.option.setNumber("Mesh.MeshSizeMin", 0.1)
gmsh.option.setNumber("Mesh.MeshSizeMax", 2)
gmsh.model.mesh.generate(2)
gmsh.write("gmsh_of_cadquery_compound_in_memory.msh")
