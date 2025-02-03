import os
import warnings
from pathlib import Path

import cadquery as cq
import gmsh
import pymoab as mb
import pytest
from pymoab import core, types

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import check_material_tags


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


@pytest.mark.parametrize(
    "filename",
    [
        "test_dagmc1.h5m",
        "out_folder1/test_dagmc2.h5m",
        Path("test_dagmc3.h5m"),
        Path("out_folder2/test_dagmc4.h5m"),
    ],
)
def test_export_dagmc_h5m_file_handel_paths_folders_strings(filename):
    """Checks that a h5m file is created"""

    box = cq.Workplane().box(1, 1, 1)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, material_tags=["mat1"])

    c2d.export_dagmc_h5m_file(filename=filename)

    assert Path(filename).is_file()

    os.system(f"rm -rf {filename}")


@pytest.mark.parametrize(
    "filename",
    [
        "test_dagmc1.vtk",
        "out_folder3/test_dagmc2.vtk",
        Path("test_dagmc3.vtk"),
        Path("out_folder4/test_dagmc4.vtk"),
    ],
)
def test_export_unstructured_mesh_file_handel_paths_folders_strings(filename):
    """Checks that a vtk file is created"""

    box = cq.Workplane().box(1, 1, 1)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, material_tags=["mat1"])

    c2d.export_unstructured_mesh_file(filename=filename)

    assert Path(filename).is_file()

    os.system(f"rm -rf {filename}")


@pytest.mark.parametrize(
    "filename",
    [
        "test_dagmc1.msh",
        "out_folder5/test_dagmc2.msh",
        Path("test_dagmc3.msh"),
        Path("out_folder6/test_dagmc4.msh"),
    ],
)
def test_export_gmsh_mesh_file_handel_paths_folders_strings(filename):
    """Checks that a vtk file is created"""

    box = cq.Workplane().box(1, 1, 1)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, material_tags=["mat1"])

    c2d.export_gmsh_mesh_file(filename=filename)

    assert Path(filename).is_file()

    os.system(f"rm -rf {filename}")


def test_check_material_tags_too_long():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_material_tags(["a" * 29], [1])
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "Material tag" in str(w[-1].message)
        assert "a" * 29 in str(w[-1].message)


@pytest.mark.parametrize(
    "scale_factor, expected_width",
    [
        (1, 10.0),
        (2, 20.0),
        (10, 100.0),
    ],
)
def test_scaling_factor_when_adding_stp(scale_factor, expected_width):

    c2d = CadToDagmc()
    c2d.add_stp_file("tests/single_cube.stp", scale_factor=scale_factor)
    c2d.export_gmsh_mesh_file(f"st_test_scaling_factor_{scale_factor}.msh")

    gmsh.initialize()
    gmsh.open(f"st_test_scaling_factor_{scale_factor}.msh")
    _, node_coords, _ = gmsh.model.mesh.getNodes()

    # Reshape the node coordinates into a 2D array
    node_coords = node_coords.reshape(-1, 3)

    # Calculate the bounding box
    min_coords = node_coords.min(axis=0)
    max_coords = node_coords.max(axis=0)

    width_x = max_coords[0] - min_coords[0]
    width_y = max_coords[1] - min_coords[1]
    width_z = max_coords[2] - min_coords[2]

    gmsh.finalize()

    assert width_x == expected_width
    assert width_y == expected_width
    assert width_z == expected_width


@pytest.mark.parametrize(
    "scale_factor, expected_width",
    [
        (1, 10.0),
        (2, 20.0),
        (10, 100.0),
    ],
)
def test_scaling_factor_when_adding_cq_object(scale_factor, expected_width):

    box = cq.Workplane("XY").box(10, 10, 10)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, scale_factor=scale_factor, material_tags=["mat1"])
    c2d.export_gmsh_mesh_file(f"cq_test_scaling_factor_{scale_factor}.msh")

    gmsh.initialize()
    gmsh.open(f"cq_test_scaling_factor_{scale_factor}.msh")
    _, node_coords, _ = gmsh.model.mesh.getNodes()

    # Reshape the node coordinates into a 2D array
    node_coords = node_coords.reshape(-1, 3)

    # Calculate the bounding box
    min_coords = node_coords.min(axis=0)
    max_coords = node_coords.max(axis=0)

    width_x = max_coords[0] - min_coords[0]
    width_y = max_coords[1] - min_coords[1]
    width_z = max_coords[2] - min_coords[2]

    gmsh.finalize()

    assert width_x == expected_width
    assert width_y == expected_width
    assert width_z == expected_width


@pytest.mark.parametrize(
    "scale_factor, expected_x_width, expected_y_width, expected_z_width",
    [
        (1, 20.0, 10.0, 10.0),
        (2, 40.0, 20.0, 20.0),
        (10, 200.0, 100.0, 100.0),
    ],
)
def test_two_box_scaling_factor_when_adding_cq_object(
    scale_factor, expected_x_width, expected_y_width, expected_z_width
):

    box = cq.Workplane("XY").box(10, 10, 10)
    box2 = cq.Workplane("XY").moveTo(10, 0).box(10, 10, 10)
    c2d = CadToDagmc()
    c2d.add_cadquery_object(box, scale_factor=scale_factor, material_tags=["mat1"])
    c2d.add_cadquery_object(box2, scale_factor=scale_factor, material_tags=["mat1"])
    c2d.export_gmsh_mesh_file(f"cq_test_2_box_scaling_factor_{scale_factor}.msh")

    gmsh.initialize()
    gmsh.open(f"cq_test_2_box_scaling_factor_{scale_factor}.msh")
    _, node_coords, _ = gmsh.model.mesh.getNodes()

    # Reshape the node coordinates into a numpy 2D array
    node_coords = node_coords.reshape(-1, 3)

    # Calculate the bounding box
    min_coords = node_coords.min(axis=0)
    max_coords = node_coords.max(axis=0)

    width_x = max_coords[0] - min_coords[0]
    width_y = max_coords[1] - min_coords[1]
    width_z = max_coords[2] - min_coords[2]

    gmsh.finalize()

    assert width_x == expected_x_width
    assert width_y == expected_y_width
    assert width_z == expected_z_width
