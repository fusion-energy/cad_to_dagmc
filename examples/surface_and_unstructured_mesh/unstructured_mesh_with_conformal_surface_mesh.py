# This example makes 3 CAD half spheres
# Meshes the 3 volumes with different resolutions
# exports the mesh to a DAGMC unstructured VTK file and a DAGMC h5m file
# The outer surface of the volume mesh should match the surface of the surface
# mesh as the same mesh parameters were used in both the surface and volume mesh.
# Additionally only volume 2 is volume meshed, while all three volumes are surface meshed

import cadquery as cq
from cad_to_dagmc import CadToDagmc
import openmc


box_cutter = cq.Workplane("XY").moveTo(0, 5).box(20, 10, 20)
inner_sphere = cq.Workplane("XY").sphere(6).cut(box_cutter)
middle_sphere = cq.Workplane("XY").sphere(6.1).cut(box_cutter).cut(inner_sphere)
outer_sphere = cq.Workplane("XY").sphere(10).cut(box_cutter).cut(inner_sphere).cut(middle_sphere)

assembly = cq.Assembly()
assembly.add(inner_sphere, name="inner_sphere")
assembly.add(middle_sphere, name="middle_sphere")
assembly.add(outer_sphere, name="outer_sphere")


model = CadToDagmc()
model.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])

dagmc_filename, umesh_filename = model.export_dagmc_h5m_file(
    filename="surface_mesh_conformal.h5m",
    set_size={
        1: 0.9,
        2: 0.1,
        3: 0.9,
    },
    unstructured_volumes=[2],
    umesh_filename="volume_mesh_conformal.vtk",  #
)


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

umesh = openmc.UnstructuredMesh(umesh_filename, library="moab")
mesh_filter = openmc.MeshFilter(umesh)
tally = openmc.Tally(name="unstructured_mesh_tally")
tally.filters = [mesh_filter]
tally.scores = ["flux"]
my_tallies = openmc.Tallies([tally])


mat1 = openmc.Material(name="mat1")
mat1.add_nuclide("H1", 1, percent_type="ao")
mat1.set_density("g/cm3", 0.001)
mat2 = openmc.Material(name="mat2")
mat2.add_nuclide("H1", 1, percent_type="ao")
mat2.set_density("g/cm3", 0.002)
mat3 = openmc.Material(name="mat3")
mat3.add_nuclide("H1", 1, percent_type="ao")
mat3.set_density("g/cm3", 0.003)
my_materials = openmc.Materials([mat1, mat2, mat3])

dag_univ = openmc.DAGMCUniverse(filename=dagmc_filename)
bound_dag_univ = dag_univ.bounded_universe()
my_geometry = openmc.Geometry(root=bound_dag_univ)

my_settings = openmc.Settings()
my_settings.batches = 10
my_settings.particles = 5000
my_settings.run_mode = "fixed source"

# Create a DT point source
my_source = openmc.IndependentSource()
my_source.space = openmc.stats.Point(my_geometry.bounding_box.center)
my_source.angle = openmc.stats.Isotropic()
my_source.energy = openmc.stats.Discrete([14e6], [1])
my_settings.source = my_source

model = openmc.model.Model(my_geometry, my_materials, my_settings, my_tallies)
sp_filename = model.run()

sp = openmc.StatePoint(sp_filename)

tally_result = sp.get_tally(name="unstructured_mesh_tally")

# normally with regular meshes I would get the mesh from the tally
# but with unstructured meshes the tally does not contain the mesh
# however we can get it from the statepoint file
# umesh = tally_result.find_filter(openmc.MeshFilter)
umesh_from_sp = sp.meshes[1]

# these trigger internal code in the mesh object so that its centroids and volumes become known.
# centroids and volumes are needed for the get_values and write_data_to_vtk steps
centroids = umesh_from_sp.centroids
mesh_vols = umesh_from_sp.volumes

flux_mean = tally_result.get_values(scores=["flux"], value="mean").reshape(umesh_from_sp.dimension)
umesh_from_sp.write_data_to_vtk(filename="tally.vtk", datasets={"mean": flux_mean})
