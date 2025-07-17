import cadquery as cq
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid
from OCP.gp import gp_Pnt
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeFace,
)
from cadquery.vis import show

# Define the 4 vertices of the tetrahedron
A = (0, 0, 0)
B = (1, 0, 0)
C = (0.5, 0.866, 0)  # Equilateral triangle base
D = (0.5, 0.289, 0.816)  # Top point (height of a regular tetrahedron)

# Convert to OCC points
pA = gp_Pnt(*A)
pB = gp_Pnt(*B)
pC = gp_Pnt(*C)
pD = gp_Pnt(*D)

# Create edges
edge_AB = BRepBuilderAPI_MakeEdge(pA, pB).Edge()
edge_BC = BRepBuilderAPI_MakeEdge(pB, pC).Edge()
edge_CA = BRepBuilderAPI_MakeEdge(pC, pA).Edge()
edge_AD = BRepBuilderAPI_MakeEdge(pA, pD).Edge()
edge_BD = BRepBuilderAPI_MakeEdge(pB, pD).Edge()
edge_CD = BRepBuilderAPI_MakeEdge(pC, pD).Edge()

# Create wires for each face
wire_ABC = BRepBuilderAPI_MakeWire(edge_AB, edge_BC, edge_CA).Wire()
wire_ABD = BRepBuilderAPI_MakeWire(edge_AB, edge_BD, edge_AD).Wire()
wire_BCD = BRepBuilderAPI_MakeWire(edge_BC, edge_CD, edge_BD).Wire()
wire_CAD = BRepBuilderAPI_MakeWire(edge_CA, edge_AD, edge_CD).Wire()

# Create faces
face_ABC = BRepBuilderAPI_MakeFace(wire_ABC).Face()
face_ABD = BRepBuilderAPI_MakeFace(wire_ABD).Face()
face_BCD = BRepBuilderAPI_MakeFace(wire_BCD).Face()
face_CAD = BRepBuilderAPI_MakeFace(wire_CAD).Face()

# Create a shell and add faces to it
shell = TopoDS_Shell()
builder = BRep_Builder()
builder.MakeShell(shell)
builder.Add(shell, face_ABC)
builder.Add(shell, face_ABD)
builder.Add(shell, face_BCD)
builder.Add(shell, face_CAD)

# Create a solid from the shell
solid = TopoDS_Solid()
builder.MakeSolid(solid)
builder.Add(solid, shell)

# Convert to a CadQuery object
result = cq.Solid(solid)
# result = cq.Workplane("XY").box(2, 1, 1) # this works so i suspect something is wrong with the way i have made a cad tet in cadquery
# assembly = cq.Assembly()
# assembly.add(result, name="tetrahedron")

from cad_to_dagmc import CadToDagmc  # installed with

# python -m pip install --extra-index-url https://shimwell.github.io/wheels moab
# python -m pip install cad_to_dagmc


my_model = CadToDagmc()
my_model.add_cadquery_object(cadquery_object=result, material_tags=["mat1"])
# tried adding via assembly but this did not help avoid the lost particles
# my_model.add_cadquery_object(cadquery_object=assembly, material_tags=["mat1"])

my_model.export_dagmc_h5m_file(filename="dagmc_tet.h5m", imprint=False)
# tried various export options but all have lost particles
# my_model.export_dagmc_h5m_file(filename='dagmc_tet.h5m', imprint=True)
# my_model.export_dagmc_h5m_file(filename='dagmc_tet.h5m', imprint=False, min_mesh_size= 1., max_mesh_size=2.)
# my_model.export_dagmc_h5m_file(filename='dagmc_tet.h5m', imprint=True, min_mesh_size= 1., max_mesh_size=2.)

import openmc  # installed with python -m pip install --extra-index-url https://shimwell.github.io/wheels openmc

dag_univ = openmc.DAGMCUniverse("dagmc_tet.h5m")
bound_dag_univ = dag_univ.bounded_universe(padding_distance=10)
my_geometry = openmc.Geometry(root=bound_dag_univ)

from matplotlib import pyplot as plt

my_geometry.plot(origin=bound_dag_univ.bounding_box.center, width=(3, 3))
plt.show()

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
