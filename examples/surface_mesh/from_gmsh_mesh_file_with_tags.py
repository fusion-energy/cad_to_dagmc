# this file makes a GMESH mesh file that contains 3D physical groups.
# these groups are then used as the material tags in the DAGMC file.


# making the GMESH file
import cad_to_dagmc
import openmc


# converting the mesh file to a DAGMC file

cad_to_dagmc.export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename="examples/surface_mesh/tagged_mesh.msh",
    # no need to specify material tags as the mesh file already has physical
    # groups which are used as material tags
    # material_tags=["shell", "insert"],
    dagmc_filename="dagmc.h5m",
)

# making use of the DAGMC file in OpenMC

openmc.config["cross_sections"] = "cross_sections.xml"

mat1 = openmc.Material(name="shell")
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)

mat2 = openmc.Material(name="insert")
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
