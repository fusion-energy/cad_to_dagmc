import os
from pathlib import Path

import dagmc_h5m_file_inspector as di
from brep_to_h5m import brep_to_h5m


class TestApiUsage:
    """Test usage cases"""

    def test_h5m_file_creation(self):
        """Checks that a h5m file is created from a brep file"""

        os.system("rm test_brep_file.h5m")
        brep_to_h5m(
            brep_filename="tests/test_brep_file.brep",
            material_tags=[
                "material_for_volume_1",
                "material_for_volume_2",
                "material_for_volume_3",
                "material_for_volume_4",
                "material_for_volume_5",
                "material_for_volume_6",
            ],
            h5m_filename="test_brep_file.h5m",
            min_mesh_size=30,
            max_mesh_size=50,
            mesh_algorithm=1,
        )

        assert Path("test_brep_file.h5m").is_file()

    def test_max_mesh_size_impacts_file_size(self):
        """Checks the reducing max_mesh_size value increases the file size"""

        os.system("rm *.h5m")
        brep_to_h5m(
            brep_filename="tests/test_brep_file.brep",
            material_tags=[
                "material_for_volume_1",
                "material_for_volume_2",
                "material_for_volume_3",
                "material_for_volume_4",
                "material_for_volume_5",
                "material_for_volume_6",
            ],
            h5m_filename="test_brep_file_10.h5m",
            min_mesh_size=20,
            max_mesh_size=19,
            mesh_algorithm=1,
        )
        brep_to_h5m(
            brep_filename="tests/test_brep_file.brep",
            material_tags=[
                "material_for_volume_1",
                "material_for_volume_2",
                "material_for_volume_3",
                "material_for_volume_4",
                "material_for_volume_5",
                "material_for_volume_6",
            ],
            h5m_filename="test_brep_file_30.h5m",
            min_mesh_size=20,
            max_mesh_size=30,
            mesh_algorithm=1,
        )

        assert Path("test_brep_file_10.h5m").is_file()
        assert Path("test_brep_file_30.h5m").is_file()

        large_file = Path("test_brep_file_10.h5m").stat().st_size
        small_file = Path("test_brep_file_30.h5m").stat().st_size
        assert small_file < large_file

    def test_h5m_file_tags(self):
        """Checks that a h5m file is created with the correct tags"""

        test_h5m_filename = "test_dagmc.h5m"
        os.system(f"rm {test_h5m_filename}")
        returned_filename = brep_to_h5m(
            brep_filename="tests/test_brep_file.brep",
            material_tags=[
                "mat1",
                "mat2",
                "mat3",
                "mat4",
                "mat5",
                "mat6",
            ],
            h5m_filename=test_h5m_filename,
            min_mesh_size=30,
            max_mesh_size=50,
            mesh_algorithm=1,
        )

        assert Path(test_h5m_filename).is_file()
        assert Path(returned_filename).is_file()
        assert test_h5m_filename == returned_filename
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1, 2, 3, 4, 5, 6]
        assert di.get_materials_from_h5m(test_h5m_filename) == [
            "mat1",
            "mat2",
            "mat3",
            "mat4",
            "mat5",
            "mat6",
        ]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat1",
            2: "mat2",
            3: "mat3",
            4: "mat4",
            5: "mat5",
            6: "mat6",
        }

    # TODO add tests to check 7 or more keys results in a value error
    # because there are only 6 volumes
