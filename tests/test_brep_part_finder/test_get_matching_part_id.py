import brep_part_finder as bpf
import pytest


def test_get_part_id_center_x():

    matching_part_number = bpf.get_matching_part_id(
        brep_part_properties={
            1: {"center_x": 2.4},
            2: {"center_x": 4.2},
            3: {"center_x": 4.1},
        },
        center_x=4.2,
    )

    assert matching_part_number == [2]


def test_get_part_id_center_x_with_tolerance():

    matching_part_number = bpf.get_matching_part_id(
        brep_part_properties={
            1: {"center_x": 2.4},
            2: {"center_x": 4.2},
            3: {"center_x": 4.1},
        },
        center_x=4.2,
        center_atol=0.1,
    )

    assert matching_part_number == [2, 3]


def test_get_part_id_center_y():

    matching_part_number = bpf.get_matching_part_id(
        brep_part_properties={1: {"center_y": 2.4}, 2: {"center_y": 4.2}}, center_y=4.2
    )

    assert matching_part_number == [2]


def test_get_part_id_center_y_not_match():
    with pytest.raises(ValueError):
        bpf.get_matching_part_id(
            brep_part_properties={1: {"center_y": 2.4}, 2: {"center_y": 4.2}},
            center_y=50,
        )


# TODO tests for all properties
# "Center_z"
# "Volume"
# "BoundingBox_xmin"
# "BoundingBox_ymin"
# "BoundingBox_zmin"
# "BoundingBox_xmax"
# "BoundingBox_ymax"
# "BoundingBox_zmax"
