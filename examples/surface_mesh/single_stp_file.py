from cad_to_dagmc import CadToDagmc

import cadquery as cq

result = cq.Workplane("XY")
spline_points = [
    (2.75, 1.5),
    (2.5, 1.75),
    (2.0, 1.5),
    (1.5, 1.0),
    (1.0, 1.25),
    (0.5, 1.0),
    (0, 1.0),
]
r = result.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
result = r.extrude(1.5)
assembly = cq.Assembly()
assembly.add(result)
assembly.save("spline_extrude.stp", exportType="STEP")


my_model = CadToDagmc()
my_model.add_stp_file(filename="spline_extrude.stp", material_tags=["mat1"])
my_model.export_dagmc_h5m_file()
