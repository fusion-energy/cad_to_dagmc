import openmc
import openmc_data_downloader as odd
from brep_to_h5m import brep_to_h5m, transport_particles_on_h5m_geometry
import math

from brep_to_h5m import (
    mesh_brep,
    mesh_to_h5m_in_memory_method,
    mesh_to_h5m_stl_method,
    transport_particles_on_h5m_geometry,
)

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
    - h5m files can be used a transport geometry in DAGMC with OpenMC 
"""


def test_transport_on_h5m_with_6_volumes():

    brep_filename = "tests/test_brep_file.brep"
    h5m_filename = "test_brep_file.h5m"
    volumes = 6
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_filename=brep_filename,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename, material_tags=material_tags
    )


def test_transport_on_h5m_with_1_volumes():

    brep_filename = "tests/one_cube.brep"
    h5m_filename = "one_cube.h5m"
    volumes = 1
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_filename=brep_filename,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename, material_tags=material_tags
    )


def test_transport_on_h5m_with_2_joined_volumes():

    brep_filename = "tests/test_two_joined_cubes.brep"
    h5m_filename = "test_two_joined_cubes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_filename=brep_filename,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename, material_tags=material_tags
    )


def test_transport_on_h5m_with_2_sep_volumes():

    brep_filename = "tests/test_two_sep_cubes.brep"
    h5m_filename = "test_two_sep_cubes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_filename=brep_filename,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename, material_tags=material_tags
    )


def test_transport_result_h5m_with_2_sep_volumes():

    brep_filename = "tests/test_two_sep_cubes.brep"
    h5m_filename = "test_two_sep_cubes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_filename=brep_filename,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    new_tally = transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename, material_tags=material_tags
    )

    brep_to_h5m(
        brep_filename=brep_filename,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )
    stl_tally = transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename, material_tags=material_tags
    )

    assert math.isclose(new_tally, stl_tally)


def test_stl_vs_in_memory_1_volume():

    brep_filename = "tests/one_cube.brep"
    volumes = 1
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    gmsh, volumes = mesh_brep(
        brep_filename=brep_filename,
        min_mesh_size=1,
        max_mesh_size=5,
        mesh_algorithm=1,
    )

    mesh_to_h5m_in_memory_method(
        volumes=volumes,
        material_tags=material_tags,
        h5m_filename="h5m_from_in_memory_method.h5m",
    )

    # a new instance of gmsh is made to keep the two methods separate
    gmsh, volumes = mesh_brep(
        brep_filename=brep_filename,
        min_mesh_size=1,
        max_mesh_size=5,
        mesh_algorithm=1,
    )

    mesh_to_h5m_stl_method(
        volumes=volumes,
        material_tags=material_tags,
        h5m_filename="h5m_from_in_stl_method.h5m",
    )

    in_memory_results = transport_particles_on_h5m_geometry(
        h5m_filename="h5m_from_in_memory_method.h5m", material_tags=material_tags
    )
    stl_results = transport_particles_on_h5m_geometry(
        h5m_filename="h5m_from_in_stl_method.h5m", material_tags=material_tags
    )

    assert math.isclose(in_memory_results, stl_results)


def test_stl_vs_in_memory_2_joined_volume():

    brep_filename = "tests/test_two_joined_cubes.brep"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    gmsh, volumes = mesh_brep(
        brep_filename=brep_filename,
        min_mesh_size=1,
        max_mesh_size=5,
        mesh_algorithm=1,
    )

    mesh_to_h5m_in_memory_method(
        volumes=volumes,
        material_tags=material_tags,
        h5m_filename="h5m_from_in_memory_method.h5m",
    )

    # a new instance of gmsh is made to keep the two methods separate
    gmsh, volumes = mesh_brep(
        brep_filename=brep_filename,
        min_mesh_size=1,
        max_mesh_size=5,
        mesh_algorithm=1,
    )

    mesh_to_h5m_stl_method(
        volumes=volumes,
        material_tags=material_tags,
        h5m_filename="h5m_from_in_stl_method.h5m",
    )

    in_memory_results = transport_particles_on_h5m_geometry(
        h5m_filename="h5m_from_in_memory_method.h5m", material_tags=material_tags
    )
    stl_results = transport_particles_on_h5m_geometry(
        h5m_filename="h5m_from_in_stl_method.h5m", material_tags=material_tags
    )

    assert math.isclose(in_memory_results, stl_results)
