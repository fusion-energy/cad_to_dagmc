# script assumes that "umesh.h5m" has been created by
# curved_cadquery_object_to_dagmc_volume_mesh.py has been

import openmc

with open("cross_sections.xml", "w") as file:
    file.write(
        """
        <?xml version='1.0' encoding='UTF-8'?>
        <cross_sections>
        <library materials="H1" path="tests/ENDFB-7.1-NNDC_H1.h5" type="neutron"/>
        </cross_sections>
        """
    )
openmc.config["cross_sections"] = "cross_sections.xml"

umesh = openmc.UnstructuredMesh("umesh.h5m", library="moab")
mesh_filter = openmc.MeshFilter(umesh)
tally = openmc.Tally(name="unstrucutred_mesh_tally")
tally.filters = [mesh_filter]
tally.scores = ["flux"]
my_tallies = openmc.Tallies([tally])


mat1 = openmc.Material()
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)
my_materials = openmc.Materials([mat1])

surf1 = openmc.Sphere(r=500, boundary_type="vacuum")
region1 = -surf1

cell1 = openmc.Cell(region=region1)
cell1.fill = mat1

my_geometry = openmc.Geometry([cell1])

my_settings = openmc.Settings()
my_settings.batches = 10
my_settings.particles = 5000
my_settings.run_mode = "fixed source"

# Create a DT point source
my_source = openmc.IndependentSource()
my_source.space = openmc.stats.Point((0, 0, 0))
my_source.angle = openmc.stats.Isotropic()
my_source.energy = openmc.stats.Discrete([14e6], [1])
my_settings.source = my_source

model = openmc.model.Model(my_geometry, my_materials, my_settings, my_tallies)
sp_filename = model.run()

sp = openmc.StatePoint(sp_filename)

tally_result = sp.get_tally(name="unstrucutred_mesh_tally")

# normally with regular meshes I would get the mesh from the tally
# but with unstrucutred meshes the tally does not contain the mesh
# however we can get it from the statepoint file
# umesh = tally_result.find_filter(openmc.MeshFilter)
umesh_from_sp = sp.meshes[1]

# these trigger internal code in the mesh object so that its centroids and volumes become known.
# centroids and volumes are needed for the get_values and write_data_to_vtk steps
centroids = umesh_from_sp.centroids
mesh_vols = umesh_from_sp.volumes

flux_mean = tally_result.get_values(scores=["flux"], value="mean").reshape(umesh_from_sp.dimension)
umesh_from_sp.write_data_to_vtk(filename="tally.vtk", datasets={"mean": flux_mean})
