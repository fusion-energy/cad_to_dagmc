import paramak

my_reactor = paramak.FlfSystemCodeReactor()
my_reactor.export_brep("test_brep_file.brep")

my_cube_1 = paramak.ExtrudeStraightShape(
    name="my_cube_1",
    points=[
        [0, 0],
        [0, 1],
        [1, 1],
        [1, 0],
    ],
    distance=1,
)

my_cubes = paramak.Reactor([my_cube_1])
my_cubes.export_brep("one_cube.brep")

my_cube_2 = paramak.ExtrudeStraightShape(
    name="my_cube_2",
    points=[
        [0, 0],
        [0, 10],
        [-10, 10],
        [-10, 0],
    ],
    distance=5,
)
my_cubes = paramak.Reactor([my_cube_1, my_cube_2])
my_cubes.export_brep("test_two_joined_cubes.brep")


my_cube_3 = paramak.ExtrudeStraightShape(
    name="my_cube_3",
    points=[
        [0, 0],
        [0, 10],
        [10, 10],
        [10, 0],
    ],
    distance=5,
)

my_cube_4 = paramak.ExtrudeStraightShape(
    name="my_cube_4",
    points=[
        [-1, 0],
        [-1, 10],
        [-10, 10],
        [-10, 0],
    ],
    distance=5,
)
my_cubes = paramak.Reactor([my_cube_3, my_cube_4])
my_cubes.export_brep("test_two_sep_cubes.brep")
