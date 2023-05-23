import unittest
import brep_part_finder as bpf


class TestShape(unittest.TestCase):
    def setUp(self):

        self.brep_part_properties = bpf.get_part_properties_from_file(
            "examples/ball_reactor.brep"
        )

    def test_number_of_parts(self):
        """Checks that all 8 of the solids in the Brep result in an entry"""

        assert len(self.brep_part_properties) == 8

    def test_dict_keys_exist(self):
        """Checks each Brep solid entry has the correct keys"""

        for entry in self.brep_part_properties.keys():
            assert "center_x" in self.brep_part_properties[entry].keys()
            assert "center_y" in self.brep_part_properties[entry].keys()
            assert "center_z" in self.brep_part_properties[entry].keys()
            assert "volume" in self.brep_part_properties[entry].keys()
            assert "bounding_box_xmin" in self.brep_part_properties[entry].keys()
            assert "bounding_box_ymin" in self.brep_part_properties[entry].keys()
            assert "bounding_box_zmin" in self.brep_part_properties[entry].keys()
            assert "bounding_box_xmax" in self.brep_part_properties[entry].keys()
            assert "bounding_box_ymax" in self.brep_part_properties[entry].keys()
            assert "bounding_box_zmax" in self.brep_part_properties[entry].keys()

    def test_dict_keys_are_correct_type(self):
        """Checks each Brep solid entry has the correct type"""

        for entry in self.brep_part_properties.keys():
            assert isinstance(self.brep_part_properties[entry]["center_x"], float)
            assert isinstance(self.brep_part_properties[entry]["center_y"], float)
            assert isinstance(self.brep_part_properties[entry]["center_z"], float)
            assert isinstance(self.brep_part_properties[entry]["volume"], float)
            assert isinstance(
                self.brep_part_properties[entry]["bounding_box_xmin"], float
            )
            assert isinstance(
                self.brep_part_properties[entry]["bounding_box_ymin"], float
            )
            assert isinstance(
                self.brep_part_properties[entry]["bounding_box_zmin"], float
            )
            assert isinstance(
                self.brep_part_properties[entry]["bounding_box_xmax"], float
            )
            assert isinstance(
                self.brep_part_properties[entry]["bounding_box_ymax"], float
            )
            assert isinstance(
                self.brep_part_properties[entry]["bounding_box_zmax"], float
            )

    def test_volumes_are_positive(self):
        """Checks each Brep solid entry has a positive value for the volume"""

        for entry in self.brep_part_properties.keys():
            assert self.brep_part_properties[entry]["volume"] > 0.0
