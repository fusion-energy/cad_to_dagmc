from cad_to_dagmc.brep_part_finder import get_part_properties_from_file
from cadquery.occ_impl.shapes import Shape


def test_input_methods_get_same_results():
    filename = "examples/ball_reactor.brep"
    part_properties_from_file = get_part_properties_from_file(filename)

    shapes = Shape.importBrep(filename)
    part_properties_from_shape = get_part_properties_from_shapes(shapes)

    assert part_properties_from_shape == part_properties_from_file
