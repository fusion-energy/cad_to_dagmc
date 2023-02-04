from cad_to_dagmc import CadToDagmc
from pathlib import Path
import dagmc_h5m_file_inspector as di
import cadquery as cq

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
"""


def test_h5m_with_single_volume_list():
    """Simple geometry, a single 4 sided shape"""

    stp_files = [
        "tests/extrude_rectangle.stp",
        "tests/single_cube.stp",
        # "tests/single_volume_thin.stp", currently slow to mesh
    ]
    h5m_files = [
        "tests/extrude_rectangle.h5m",
        "tests/single_cube.h5m",
        # "tests/single_volume_thin.h5m", currently slow to mesh
    ]

    for stp_file, h5m_file in zip(stp_files, h5m_files):
        my_model = CadToDagmc()
        my_model.add_stp_file(filename=stp_file, material_tags=["mat1"])
        my_model.export_dagmc_h5m_file(filename=h5m_file)

        assert di.get_volumes_and_materials_from_h5m(h5m_file) == {1: "mat1"}


def test_h5m_with_multi_volume_not_touching():
    stp_files = [
        "tests/two_disconnected_cubes.stp",
    ]
    material_tags = [
        ["mat1", "mat2"],
    ]
    h5m_files = [
        "tests/two_disconnected_cubes.h5m",
    ]
    for stp_file, mat_tags, h5m_file in zip(stp_files, material_tags, h5m_files):
        my_model = CadToDagmc()
        my_model.add_stp_file(filename=stp_file, material_tags=mat_tags)

        assert my_model.material_tags == mat_tags
        # merged_cad_obj = cad_to_dagmc.merge_surfaces(stp_file_object)
        my_model.export_dagmc_h5m_file(filename=h5m_file)

        tags_dict = {}
        for counter, loop_mat_tag in enumerate(mat_tags, 1):
            tags_dict[counter] = loop_mat_tag
        assert di.get_volumes_and_materials_from_h5m(h5m_file) == tags_dict


def test_h5m_with_multi_volume_touching():
    stp_files = [
        "tests/multi_volume_cylinders.stp",
        "tests/two_connected_cubes.stp",
    ]
    material_tags = [
        ["mat1", "mat2", "mat3", "mat4", "mat5", "mat6"],
        ["mat1", "mat2"],
    ]
    h5m_files = [
        "tests/multi_volume_cylinders.h5m",
        "tests/two_connected_cubes.h5m",
    ]
    for stp_file, mat_tags, h5m_file in zip(stp_files, material_tags, h5m_files):
        my_model = CadToDagmc()
        my_model.add_stp_file(stp_file, material_tags=mat_tags)

        assert my_model.material_tags == mat_tags

        # merged_cad_obj = cad_to_dagmc.merge_surfaces(stp_file_object)
        my_model.export_dagmc_h5m_file(filename=h5m_file)

        tags_dict = {}
        for counter, loop_mat_tag in enumerate(mat_tags, 1):
            tags_dict[counter] = loop_mat_tag
        assert di.get_volumes_and_materials_from_h5m(h5m_file) == tags_dict


def test_cq_compound():
    # make other shapes from the CadQuery examples
    spline_points = [
        (2.75, 1.5),
        (2.5, 1.75),
        (2.0, 1.5),
        (1.5, 1.0),
        (1.0, 1.25),
        (0.5, 1.0),
        (0, 1.0),
    ]

    s = cq.Workplane("XY")
    r = (
        s.lineTo(3.0, 0)
        .lineTo(3.0, 1.0)
        .spline(spline_points, includeCurrent=True)
        .close()
    )
    cq_shape_1 = r.extrude(-1)

    s2 = cq.Workplane("XY")
    r2 = (
        s2.lineTo(3.0, 0)
        .lineTo(3.0, 1.0)
        .spline(spline_points, includeCurrent=True)
        .close()
    )
    cq_shape_2 = r2.extrude(1)

    compound_of_workplanes = cq.Compound.makeCompound(
        [cq_shape_1.val(), cq_shape_2.val()]
    )

    my_model = CadToDagmc()
    my_model.add_cadquery_object(
        object=compound_of_workplanes, material_tags=["mat1", "mat2"]
    )
    my_model.export_dagmc_h5m_file(
        filename="compound_dagmc.h5m", max_mesh_size=0.2, min_mesh_size=0.1
    )

    assert Path("compound_dagmc.h5m").is_file()
    assert di.get_volumes_and_materials_from_h5m("compound_dagmc.h5m") == {
        1: "mat1",
        2: "mat2",
    }
