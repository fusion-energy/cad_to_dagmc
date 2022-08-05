# import dagmc_h5m_file_inspector as di
import cad_to_dagmc
from vertices_to_h5m import vertices_to_h5m
import dagmc_h5m_file_inspector as di

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags

"""


from cadquery import importers
from OCP.GCPnts import GCPnts_QuasiUniformDeflection

# from cadquery.occ_impl import shapes
import OCP
import cadquery as cq
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation


def test_h5m_with_single_volume_list():
    #     """The simplest geometry, a single 4 sided shape with lists instead of np arrays"""

    stp_files = ["tests/extrude_rectangle.stp", "tests/single_cube.stp"]
    h5m_files = ["tests/extrude_rectangle.h5m", "tests/single_cube.h5m"]

    for stp_file, h5m_file in zip(stp_files, h5m_files):

        merged_cad_obj = cad_to_dagmc.load_stp_file(stp_file)

        # merged_stp_file = cad_to_dagmc.merge_surfaces(stp_file)
        vertices, triangles = cad_to_dagmc.tessellate(merged_cad_obj, tolerance=2)

        vertices_to_h5m(
            vertices=vertices,
            triangles=triangles,
            material_tags=["mat1"],
            h5m_filename=h5m_file,
        )

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

        merged_cad_obj = cad_to_dagmc.load_stp_file(stp_file)
        # merged_cad_obj = cad_to_dagmc.merge_surfaces(stp_file_object)
        vertices, triangles = cad_to_dagmc.tessellate(merged_cad_obj, tolerance=2)

        vertices_to_h5m(
            vertices=vertices,
            triangles=triangles,
            material_tags=mat_tags,
            h5m_filename=h5m_file,
        )

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

        merged_cad_obj = cad_to_dagmc.load_stp_file(stp_file)
        # merged_cad_obj = cad_to_dagmc.merge_surfaces(stp_file_object)
        vertices, triangles = cad_to_dagmc.tessellate(merged_cad_obj, tolerance=2)

        vertices_to_h5m(
            vertices=vertices,
            triangles=triangles,
            material_tags=mat_tags,
            h5m_filename=h5m_file,
        )

        tags_dict = {}
        for counter, loop_mat_tag in enumerate(mat_tags, 1):
            tags_dict[counter] = loop_mat_tag
        assert di.get_volumes_and_materials_from_h5m(h5m_file) == tags_dict
