from cad_to_dagmc import CadToDagmc
import cadquery as cq

# see Cadquery docs for lots of examples
# https://cadquery.readthedocs.io/en/latest/examples.html
box = cq.Workplane("XY").moveTo(2, 0).box(2, 2, 2)
box_with_round_corners = cq.Workplane("XY").box(2, 1, 1)

my_model = CadToDagmc()
my_model.add_cadquery_object(cadquery_object=box, material_tags=["mat1"])
my_model.add_cadquery_object(cadquery_object=box_with_round_corners, material_tags=["mat2"])
my_model.export_dagmc_h5m_file()
