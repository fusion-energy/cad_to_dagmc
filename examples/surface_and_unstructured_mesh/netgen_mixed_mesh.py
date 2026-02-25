"""Example: Mixed surface + volume mesh using the Netgen backend.

Creates a box with a spherical cutout and a sphere. The sphere gets a
tetrahedral volume mesh (for unstructured mesh tallies) while the box
gets a minimal surface-only mesh (for DAGMC tracking). The shared face
between the two volumes is kept conformal automatically.

Requires: pip install cad_to_dagmc[netgen]
"""

from cad_to_dagmc import CadToDagmc
import cadquery as cq

# Build geometry: box with spherical void + sphere insert
assembly = cq.Assembly()
box = cq.Workplane("XY").box(30, 30, 30)
sphere = cq.Workplane("XY").moveTo(20, 0).sphere(10)
assembly.add(box.cut(sphere), name="box")
assembly.add(sphere, name="sphere")

my_model = CadToDagmc()
my_model.add_cadquery_object(
    cadquery_object=assembly,
    material_tags="assembly_names",
)

# Export with the netgen backend:
#   - "box" gets a minimal surface mesh (flat faces = 2 triangles each)
#   - "sphere" gets a tetrahedral volume mesh with equilateral tets
#   - The shared curved face between box and sphere is meshed by netgen
#     so it is conformal with the tet mesh
my_model.export_dagmc_h5m_file(
    filename="dagmc.h5m",
    meshing_backend="netgen",
    tolerance=0.1,
    angular_tolerance=0.1,
    tet_volumes=["sphere"],
    target_edge_length=2.0,
    grading=0.05,
)
