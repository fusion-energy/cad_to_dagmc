import cadquery
from cadquery import Assembly

result = cadquery.Workplane("XY").box(1., 1., 1.)
assembly = Assembly()
assembly.add(result)
assembly.save("single_cube.stp", exportType="STEP")


result1 = cadquery.Workplane("XY").box(10., 10., 5.)
result2 = cadquery.Workplane("XY").moveTo(10, 0).box(10., 10., 5.)
assembly = Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("test_two_joined_cubes.stp", exportType="STEP")


result1 = cadquery.Workplane("XY").box(10., 10., 5.)
result2 = cadquery.Workplane("XY").moveTo(11, 0).box(10., 10., 5.)
assembly = Assembly()
assembly.add(result1)
assembly.add(result2)
assembly.save("test_two_sep_cubes.stp", exportType="STEP")
