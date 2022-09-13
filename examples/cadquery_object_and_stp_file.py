from cad_to_dagmc import CadToDagmc
import cadquery as cq

# make other shapes from the CadQuery examples
s = cq.Workplane("XY")
spline_points = [
    (2.75, 1.5),
    (2.5, 1.75),
    (2.0, 1.5),
    (1.5, 1.0),
    (1.0, 1.25),
    (0.5, 1.0),
    (0, 1.0)
]
r = s.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
result = r.extrude(-1)

my_model = CadToDagmc()
my_model.add_cadquery_object(object=result, material_tags=['mat1'])
my_model.add_stp_file(filename='examples/single_cube.stp', material_tags=['mat2'], scale_factor=0.1)
my_model.export_dagmc_h5m_file(max_mesh_size=0.2, min_mesh_size=0.1)
