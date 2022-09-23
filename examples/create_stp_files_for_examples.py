import cadquery
from cadquery import Assembly
from math import pi, cos, sin, floor

result = cadquery.Workplane("XY").box(1.0, 1.0, 1.0)
assembly = Assembly()
assembly.add(result)
assembly.save("single_cube.stp", exportType="STEP")


result1 = cadquery.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cadquery.Workplane("XY").moveTo(10, 0).box(10.0, 10.0, 5.0)
assembly = Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("two_connected_cubes.stp", exportType="STEP")


result1 = cadquery.Workplane("XY").box(10.0, 10.0, 5.0)
result2 = cadquery.Workplane("XY").moveTo(11, 0).box(10.0, 10.0, 5.0)
assembly = Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("two_separate_cubes.stp", exportType="STEP")


result = sphere = cadquery.Workplane().moveTo(100, 0).sphere(5)
assembly = Assembly()
assembly.add(result)
assembly.save("single_sphere.stp", exportType="STEP")


result = cadquery.Workplane().text(txt="DAGMC", fontsize=10, distance=1)
assembly = Assembly()
assembly.add(result)
assembly.save("text_dagmc.stp", exportType="STEP")


result = cadquery.Workplane("XY")
spline_points = [
    (2.75, 1.5),
    (2.5, 1.75),
    (2.0, 1.5),
    (1.5, 1.0),
    (1.0, 1.25),
    (0.5, 1.0),
    (0, 1.0),
]
r = (
    result.lineTo(3.0, 0)
    .lineTo(3.0, 1.0)
    .spline(spline_points, includeCurrent=True)
    .close()
)
result = r.extrude(1.5)
assembly = Assembly()
assembly.add(result)
assembly.save("spline_extrude.stp", exportType="STEP")


# define the generating function
def hypocycloid(t, r1, r2):
    return (
        (r1 - r2) * cos(t) + r2 * cos(r1 / r2 * t - t),
        (r1 - r2) * sin(t) + r2 * sin(-(r1 / r2 * t - t)),
    )


def epicycloid(t, r1, r2):
    return (
        (r1 + r2) * cos(t) - r2 * cos(r1 / r2 * t + t),
        (r1 + r2) * sin(t) - r2 * sin(r1 / r2 * t + t),
    )


def gear(t, r1=4, r2=1):
    if (-1) ** (1 + floor(t / 2 / pi * (r1 / r2))) < 0:
        return epicycloid(t, r1, r2)
    else:
        return hypocycloid(t, r1, r2)


# create the gear profile and extrude it
result = (
    cadquery.Workplane("XY")
    .parametricCurve(lambda t: gear(t * 2 * pi, 6, 1))
    .twistExtrude(15, 90)
    .faces(">Z")
    .workplane()
    .circle(2)
    .cutThruAll()
)
assembly = Assembly()
assembly.add(result)
assembly.save("curved_extrude.stp", exportType="STEP")
