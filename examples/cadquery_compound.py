from cad_to_dagmc import CadToDagmc
import cadquery as cq

# make other shapes from the CadQuery examples
spline_points = [
    (2.75, 1.5),
    (2.5, 1.75),
    (2.0, 1.5),
    (1.5, 1.0),
    (1.0, 1.25),
    (0.5, 1.0),
    (0, 1.0),
]

s = cq.Workplane("XY")
r = s.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
cq_shape_1 = r.extrude(-1)

s2 = cq.Workplane("XY")
r2 = (
    s2.lineTo(3.0, 0)
    .lineTo(3.0, 1.0)
    .spline(spline_points, includeCurrent=True)
    .close()
)
cq_shape_2 = r2.extrude(1)


compound_of_shapes = cq.Compound.makeCompound([cq_shape_1.val(), cq_shape_2.val()])

my_model = CadToDagmc()
my_model.add_cadquery_object(object=compound_of_shapes, material_tags=["mat1", "mat2"])
my_model.export_dagmc_h5m_file(max_mesh_size=0.2, min_mesh_size=0.1)
