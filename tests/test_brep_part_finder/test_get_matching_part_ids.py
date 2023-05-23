import brep_part_finder as bpf
import pytest


def test_get_matching_part_ids_order():

    matching_part_numbers = bpf.get_matching_part_ids(
        brep_part_properties={
            1: {"center_x": 2.4},
            2: {"center_x": 4.2},
            3: {"center_x": 4.1},
        },
        shape_properties={
            1: {"center_x": 4.1},
            2: {"center_x": 4.2},
            3: {"center_x": 2.4},
        },
    )

    assert matching_part_numbers == [(1, 3), (2, 2), (3, 1)]


def test_get_matching_part_ids_order_2():
    matching_part_numbers = bpf.get_matching_part_ids(
        brep_part_properties={
            1: {"center_x": 4.1},
            2: {"center_x": 4.2},
            3: {"center_x": 2.4},
        },
        shape_properties={
            1: {"center_x": 4.1},
            2: {"center_x": 4.2},
            3: {"center_x": 2.4},
        },
    )

    assert matching_part_numbers == [(1, 1), (2, 2), (3, 3)]


def test_get_matching_part_ids_order_3():
    matching_part_numbers = bpf.get_matching_part_ids(
        brep_part_properties={
            1: {"center_x": 2.4},
            2: {"center_x": 4.1},
            3: {"center_x": 4.2},
        },
        shape_properties={
            1: {"center_x": 4.1},
            2: {"center_x": 4.2},
            3: {"center_x": 2.4},
        },
    )

    assert matching_part_numbers == [(1, 3), (2, 1), (3, 2)]
