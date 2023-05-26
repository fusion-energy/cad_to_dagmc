from cad_to_dagmc import brep_part_finder as bpf

brep_part_properties = bpf.get_part_properties_from_file(
    "tests/test_brep_part_finder/ball_reactor.brep"
)


def test_number_of_parts():
    """Checks that all 8 of the solids in the Brep result in an entry"""

    assert len(brep_part_properties) == 8


def test_dict_keys_exist():
    """Checks each Brep solid entry has the correct keys"""

    for entry in brep_part_properties.keys():
        assert "center_x" in brep_part_properties[entry].keys()
        assert "center_y" in brep_part_properties[entry].keys()
        assert "center_z" in brep_part_properties[entry].keys()
        assert "volume" in brep_part_properties[entry].keys()
        assert "bounding_box_xmin" in brep_part_properties[entry].keys()
        assert "bounding_box_ymin" in brep_part_properties[entry].keys()
        assert "bounding_box_zmin" in brep_part_properties[entry].keys()
        assert "bounding_box_xmax" in brep_part_properties[entry].keys()
        assert "bounding_box_ymax" in brep_part_properties[entry].keys()
        assert "bounding_box_zmax" in brep_part_properties[entry].keys()


def test_dict_keys_are_correct_type():
    """Checks each Brep solid entry has the correct type"""

    for entry in brep_part_properties.keys():
        assert isinstance(brep_part_properties[entry]["center_x"], float)
        assert isinstance(brep_part_properties[entry]["center_y"], float)
        assert isinstance(brep_part_properties[entry]["center_z"], float)
        assert isinstance(brep_part_properties[entry]["volume"], float)
        assert isinstance(brep_part_properties[entry]["bounding_box_xmin"], float)
        assert isinstance(brep_part_properties[entry]["bounding_box_ymin"], float)
        assert isinstance(brep_part_properties[entry]["bounding_box_zmin"], float)
        assert isinstance(brep_part_properties[entry]["bounding_box_xmax"], float)
        assert isinstance(brep_part_properties[entry]["bounding_box_ymax"], float)
        assert isinstance(brep_part_properties[entry]["bounding_box_zmax"], float)


def test_volumes_are_positive():
    """Checks each Brep solid entry has a positive value for the volume"""

    for entry in brep_part_properties.keys():
        assert brep_part_properties[entry]["volume"] > 0.0
