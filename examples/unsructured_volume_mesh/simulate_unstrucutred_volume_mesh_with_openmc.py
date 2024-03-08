# script assumes that "umesh.h5m" has been created by
# curved_cadquery_object_to_dagmc_volume_mesh.py has been

import openmc

umesh = openmc.UnstructuredMesh("umesh.h5m", library="moab")
mesh_filter = openmc.MeshFilter(umesh)
tally = openmc.Tally(name="t1")
tally.filters = [mesh_filter]
tally.scores = ["flux"]
tally.estimator = "tracklength"
my_tallies = openmc.Tallies([tally])


mat1 = openmc.Material()
mat1.add_element("Pb", 84.2, percent_type="ao")
mat1.add_element(
    "Li",
    15.8,
    percent_type="ao",
    enrichment=50.0,
    enrichment_target="Li6",
    enrichment_type="ao",
)
mat1.set_density("g/cm3", 11)
my_materials = openmc.Materials([mat1])

surf1 = openmc.Sphere(r=500, boundary_type="vacuum")
region1 = -surf1

cell1 = openmc.Cell(region=region1)
cell1.fill = mat1

my_geometry = openmc.Geometry([cell1])


my_settings = openmc.Settings()
my_settings.batches = 10
my_settings.inactive = 0
my_settings.particles = 5000
my_settings.run_mode = "fixed source"

# Create a DT point source
my_source = openmc.Source()
# my_source = openmc.IndependentSource()
my_source.space = openmc.stats.Point((0, 0, 0))
my_source.angle = openmc.stats.Isotropic()
my_source.energy = openmc.stats.Discrete([14e6], [1])
my_settings.source = my_source

model = openmc.model.Model(my_geometry, my_materials, my_settings, my_tallies)
sp_filename = model.run()

sp = openmc.StatePoint(sp_filename)

tally_result = sp.get_tally(name="t1")


# umesh = tally_result.find_filter(openmc.MeshFilter)
umesh_from_sp = sp.meshes[1]

centroids = umesh_from_sp.centroids
mesh_vols = umesh_from_sp.volumes

flux_mean = tally_result.get_values(scores=["flux"], value="mean").reshape(
    umesh_from_sp.dimension
)
umesh_from_sp.write_data_to_vtk(filename="tally.vtk", datasets={"mean": flux_mean})
