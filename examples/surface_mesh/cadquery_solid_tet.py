import cadquery as cq
from cadquery.vis import show_object



import numpy as np
import cadquery as cq

from cadquery.vis import show

# Define the 4 vertices of the tetrahedron
A = cq.Vector(0, 0, 0)
B = cq.Vector(1, 0, 0)
C = cq.Vector(0, 1, 0)
D = cq.Vector(0, 0, 1)

# Create the 4 triangular faces of the tetrahedron
f1 = cq.Face.makeFromWires(cq.Wire.makePolygon([A, B, C, A]))
f2 = cq.Face.makeFromWires(cq.Wire.makePolygon([A, B, D, A]))
f3 = cq.Face.makeFromWires(cq.Wire.makePolygon([A, C, D, A]))
f4 = cq.Face.makeFromWires(cq.Wire.makePolygon([B, C, D, B]))

# Make a shell from the faces
shell = cq.Shell.makeShell([f1, f2, f3, f4])

# Convert shell to a solid
result = cq.Solid.makeSolid(shell)

# Display
# show_object(result)



from cad_to_dagmc import CadToDagmc  # installed with

# python -m pip install --extra-index-url https://shimwell.github.io/wheels moab
# python -m pip install cad_to_dagmc


my_model = CadToDagmc()
my_model.add_cadquery_object(cadquery_object=result, material_tags=["mat1"])
my_model.export_dagmc_h5m_file(filename='dagmc_tet.h5m', imprint=False, min_mesh_size= 2., max_mesh_size=4.)

import openmc  # installed with python -m pip install --extra-index-url https://shimwell.github.io/wheels openmc

dag_univ = openmc.DAGMCUniverse("dagmc_tet.h5m")
bound_dag_univ = dag_univ.bounded_universe(padding_distance=10)
my_geometry = openmc.Geometry(root=bound_dag_univ)

from matplotlib import pyplot as plt
my_geometry.plot(origin=bound_dag_univ.bounding_box.center, width=(3,3))
# plt.show()

mat1 = openmc.Material(name="mat1")
mat1.add_nuclide("Li7", 1, percent_type="ao")
mat1.set_density("g/cm3", 100)
my_materials = openmc.Materials([mat1])

my_settings = openmc.Settings()
my_settings.batches = 10
my_settings.particles = 50
my_settings.run_mode = "fixed source"

my_source = openmc.IndependentSource()
my_source.space = openmc.stats.Point(
    bound_dag_univ.bounding_box.center
)  # source in the center of the bounding box
my_source.angle = openmc.stats.Isotropic()
my_source.energy = openmc.stats.Discrete([14e6], [1])
my_settings.source = my_source

model = openmc.model.Model(my_geometry, my_materials, my_settings)

model.run()
