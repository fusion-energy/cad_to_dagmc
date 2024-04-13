# this file makes a GMESH mesh file from a Step file
# then loads up the GMESH file and converts it to a DAGMC file


# making the GMESH file
from cad_to_dagmc import CadToDagmc
import cadquery as cq

result1 = cq.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cq.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = cq.Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("two_connected_cubes.stp", exportType="STEP")

geometry = CadToDagmc()
geometry.add_stp_file("two_connected_cubes.stp")
geometry.export_gmsh_mesh_file(filename="example_gmsh_mesh.msh")

# converting the mesh file to a DAGMC file
from cad_to_dagmc import MeshToDagmc

mesh = MeshToDagmc(filename="example_gmsh_mesh.msh")

mesh.export_dagmc_h5m_file(
    material_tags=["mat1", "mat2"],
    filename="dagmc.h5m",
)

# making use of the DAGMC file in OpenMC
import openmc

openmc.config["cross_sections"] = "cross_sections.xml"

mat1 = openmc.Material(name="mat1")
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)

mat2 = openmc.Material(name="mat2")
mat2.add_nuclide("H1", 1, percent_type="ao")
mat2.set_density("g/cm3", 0.002)

materials = openmc.Materials([mat1, mat2])

universe = openmc.DAGMCUniverse("dagmc.h5m").bounded_universe()
geometry = openmc.Geometry(universe)

my_settings = openmc.Settings()
my_settings.batches = 10
my_settings.inactive = 0
my_settings.particles = 500
my_settings.run_mode = "fixed source"

model = openmc.Model(geometry=geometry, materials=materials, settings=my_settings)
model.run()
