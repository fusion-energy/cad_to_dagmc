import brep_part_finder as bpf
from cadquery.occ_impl.shapes import Shape


def test_input_methods_get_same_results():

    filename = "examples/ball_reactor.brep"
    part_properties_from_file = bpf.get_part_properties_from_file(filename)

    shapes = Shape.importBrep(filename)
    part_properties_from_shape = bpf.get_part_properties_from_shapes(shapes)

    assert part_properties_from_shape == part_properties_from_file
