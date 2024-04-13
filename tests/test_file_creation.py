from cad_to_dagmc import CadToDagmc, MeshToDagmc
from pathlib import Path
import cadquery as cq
import pymoab as mb
from pymoab import core, types

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
"""


def get_volumes_and_materials_from_h5m(filename: str) -> dict:
    """Reads in a DAGMC h5m file and uses PyMoab to find the volume ids with
    their associated material tags.

    Arguments:
        filename: the filename of the DAGMC h5m file

    Returns:
        A dictionary of volume ids and material tags
    """

    mbcore = core.Core()
    mbcore.load_file(filename)
    category_tag = mbcore.tag_get_handle(mb.types.CATEGORY_TAG_NAME)
    group_category = ["Group"]
    group_ents = mbcore.get_entities_by_type_and_tag(
        0, mb.types.MBENTITYSET, category_tag, group_category
    )
    name_tag = mbcore.tag_get_handle(mb.types.NAME_TAG_NAME)
    id_tag = mbcore.tag_get_handle(mb.types.GLOBAL_ID_TAG_NAME)
    vol_mat = {}
    for group_ent in group_ents:
        group_name = mbcore.tag_get_data(name_tag, group_ent)[0][0]
        # confirm that this is a material!
        if group_name.startswith("mat:"):
            vols = mbcore.get_entities_by_type(group_ent, mb.types.MBENTITYSET)
            for vol in vols:
                id = mbcore.tag_get_data(id_tag, vol)[0][0].item()
                vol_mat[id] = group_name
    return vol_mat


def test_h5m_with_single_volume_list():
    """Simple geometry, a single 4 sided shape"""

    h5m_file = "tests/single_cube.h5m"
    mesh_file = "test.msh"
    my_model = CadToDagmc()
    my_model.add_stp_file(filename="tests/single_cube.stp", material_tags=["mat1"])
    my_model.export_dagmc_h5m_file(filename=h5m_file)
    my_model.export_gmsh_mesh_file(filename=mesh_file)
    assert Path(mesh_file).is_file()
    my_model.export_gmsh_mesh_file(filename="test3d.msh", dimensions=3)
    assert Path("test3d.msh").is_file()
    assert get_volumes_and_materials_from_h5m(h5m_file) == {1: "mat:mat1"}

    h5m_file = "tests/single_cube_from_mesh.h5m"
    my_model2 = MeshToDagmc(mesh_file)
    my_model2.export_dagmc_h5m_file(filename=h5m_file, material_tags=["mat2"])
    assert Path(h5m_file).is_file()
    assert get_volumes_and_materials_from_h5m(h5m_file) == {1: "mat:mat2"}


def test_h5m_with_single_volume_2():
    """Simple geometry, a single 4 sided shape"""

    h5m_file = "tests/curved_extrude.h5m"

    my_model = CadToDagmc()
    my_model.add_stp_file(filename="tests/curved_extrude.stp", material_tags=["mat1"])
    my_model.export_dagmc_h5m_file(filename=h5m_file)

    assert get_volumes_and_materials_from_h5m(h5m_file) == {1: "mat:mat1"}


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

        my_model.export_dagmc_h5m_file(filename=h5m_file)

        tags_dict = {}
        for counter, loop_mat_tag in enumerate(mat_tags, 1):
            tags_dict[counter] = f"mat:{loop_mat_tag}"
        assert get_volumes_and_materials_from_h5m(h5m_file) == tags_dict


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

        my_model.export_dagmc_h5m_file(filename=h5m_file)
        my_model.export_gmsh_mesh_file(filename=h5m_file + ".msh")

        tags_dict = {}
        for counter, loop_mat_tag in enumerate(mat_tags, 1):
            tags_dict[counter] = f"mat:{loop_mat_tag}"
        assert get_volumes_and_materials_from_h5m(h5m_file) == tags_dict

        my_model2 = MeshToDagmc(filename=h5m_file + ".msh")
        my_model2.export_dagmc_h5m_file(filename=h5m_file, material_tags=mat_tags)
        assert get_volumes_and_materials_from_h5m(h5m_file) == tags_dict


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
    r = s.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
    cq_shape_1 = r.extrude(-1)

    s2 = cq.Workplane("XY")
    r2 = s2.lineTo(3.0, 0).lineTo(3.0, 1.0).spline(spline_points, includeCurrent=True).close()
    cq_shape_2 = r2.extrude(1)

    compound_of_workplanes = cq.Compound.makeCompound([cq_shape_1.val(), cq_shape_2.val()])

    my_model = CadToDagmc()
    my_model.add_cadquery_object(
        cadquery_object=compound_of_workplanes,
        material_tags=["mat1", "mat2"],
    )
    my_model.export_dagmc_h5m_file(
        filename="compound_dagmc.h5m",
        max_mesh_size=0.2,
        min_mesh_size=0.1,
    )

    assert Path("compound_dagmc.h5m").is_file()
    assert get_volumes_and_materials_from_h5m("compound_dagmc.h5m") == {
        1: "mat:mat1",
        2: "mat:mat2",
    }


def test_gmsh_mesh_with_single_volume_list():
    """Simple geometry, a single 4 sided shape"""

    gmsh_mesh_file = "tests/single_cube.msh"

    my_model = CadToDagmc()
    my_model.add_stp_file(filename="tests/single_cube.stp")
    my_model.export_gmsh_mesh_file(filename=gmsh_mesh_file)
    my_model.export_gmsh_mesh_file(filename="test2.msh")
    assert Path("test2.msh").is_file()
    assert Path("tests/single_cube.msh").is_file()
    my_model.export_gmsh_mesh_file(filename="test2_3d.msh", dimensions=3)
    assert Path("test2_3d.msh").is_file()


def test_gmsh_mesh_with_single_volume_2():
    """Simple geometry, a single 4 sided shape"""

    gmsh_mesh_file = "tests/curved_extrude.msh"

    my_model = CadToDagmc()
    my_model.add_stp_file(filename="tests/curved_extrude.stp")
    my_model.export_gmsh_mesh_file(filename=gmsh_mesh_file)


def test_gmsh_mesh_with_multi_volume_not_touching():
    stp_files = [
        "tests/two_disconnected_cubes.stp",
    ]
    material_tags = [
        ["mat1", "mat2"],
    ]
    gmsh_mesh_files = [
        "tests/two_disconnected_cubes.msh",
    ]
    for stp_file, mat_tags, gmsh_mesh_file in zip(stp_files, material_tags, gmsh_mesh_files):
        my_model = CadToDagmc()
        my_model.add_stp_file(filename=stp_file, material_tags=mat_tags)

        my_model.export_gmsh_mesh_file(filename=gmsh_mesh_file)


def test_gmsh_mesh_with_multi_volume_touching():
    stp_files = [
        "tests/multi_volume_cylinders.stp",
        "tests/two_connected_cubes.stp",
    ]
    material_tags = [
        ["mat1", "mat2", "mat3", "mat4", "mat5", "mat6"],
        ["mat1", "mat2"],
    ]
    gmsh_mesh_files = [
        "tests/multi_volume_cylinders.msh",
        "tests/two_connected_cubes.msh",
    ]
    for stp_file, mat_tags, gmsh_mesh_file in zip(stp_files, material_tags, gmsh_mesh_files):
        my_model = CadToDagmc()
        my_model.add_stp_file(stp_file, material_tags=mat_tags)

        my_model.export_gmsh_mesh_file(filename=gmsh_mesh_file)

        tags_dict = {}
        for counter, loop_mat_tag in enumerate(mat_tags, 1):
            tags_dict[counter] = f"mat:{loop_mat_tag}"
