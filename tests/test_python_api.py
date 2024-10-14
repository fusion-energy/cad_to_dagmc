import os
from pathlib import Path
import cadquery as cq
from cad_to_dagmc import CadToDagmc


from pathlib import Path

import pymoab as mb
from pymoab import core, types


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


def test_max_mesh_size_impacts_file_size():
    """Checks the reducing max_mesh_size value increases the file size"""

    sphere = cq.Workplane().sphere(100)

    c2d = CadToDagmc()
    c2d.add_cadquery_object(sphere, material_tags=["m1"])
    os.system("rm *.h5m")
    c2d.export_dagmc_h5m_file(
        min_mesh_size=10,
        max_mesh_size=20,
        mesh_algorithm=1,
        filename="test_10_30.h5m",
    )
    c2d.export_dagmc_h5m_file(
        min_mesh_size=20,
        max_mesh_size=30,
        mesh_algorithm=1,
        filename="test_20_30.h5m",
    )
    c2d.export_dagmc_h5m_file(
        min_mesh_size=20,
        max_mesh_size=25,
        mesh_algorithm=1,
        filename="test_20_25.h5m",
    )

    assert Path("test_10_30.h5m").is_file()
    assert Path("test_20_30.h5m").is_file()
    assert Path("test_20_25.h5m").is_file()

    large_file = Path("test_10_30.h5m").stat().st_size
    small_file = Path("test_20_30.h5m").stat().st_size
    medium_file = Path("test_20_25.h5m").stat().st_size
    assert small_file < large_file
    assert small_file < medium_file


def test_h5m_file_tags():
    """Checks that a h5m file is created with the correct tags"""

    sphere1 = cq.Workplane().sphere(20)
    sphere2 = cq.Workplane().moveTo(100, 100).sphere(20)
    sphere3 = cq.Workplane().moveTo(-100, -100).sphere(20)

    c2d = CadToDagmc()
    c2d.add_cadquery_object(sphere1, material_tags=["mat1"])
    c2d.add_cadquery_object(sphere2, material_tags=["mat2"])
    c2d.add_cadquery_object(sphere3, material_tags=["mat3"])

    test_h5m_filename = "test_dagmc.h5m"
    os.system(f"rm {test_h5m_filename}")

    returned_filename = c2d.export_dagmc_h5m_file(filename=test_h5m_filename)

    assert Path(test_h5m_filename).is_file()
    assert Path(returned_filename).is_file()
    assert test_h5m_filename == returned_filename

    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat:mat1",
        2: "mat:mat2",
        3: "mat:mat3",
    }


def test_add_cadquery_object_returned_volumes():
    """Checks that a add_cadquery_object method returns the correct number of volumes"""

    sphere1 = cq.Workplane().sphere(20)
    sphere2 = cq.Workplane().moveTo(100, 100).sphere(20)
    sphere3 = cq.Workplane().moveTo(-100, -100).sphere(20)

    c2d = CadToDagmc()
    vols = c2d.add_cadquery_object(sphere1, material_tags=["mat1"])
    assert vols == 1

    assembly = cq.Assembly()
    assembly.add(sphere1)
    assembly.add(sphere2)
    assembly.add(sphere3)
    c2d = CadToDagmc()
    vols = c2d.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])
    assert vols == 3


def test_add_stp_file_returned_volumes():
    """Checks that a add_stp_file method returns the correct number of volumes"""

    c2d = CadToDagmc()
    vols = c2d.add_stp_file("tests/curved_extrude.stp")
    assert vols == 1

    c2d = CadToDagmc()
    vols = c2d.add_stp_file("tests/two_disconnected_cubes.stp")
    assert vols == 2
