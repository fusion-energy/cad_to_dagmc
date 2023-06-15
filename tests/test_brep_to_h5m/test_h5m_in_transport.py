import openmc
from cad_to_dagmc.brep_to_h5m import brep_to_h5m
import math
import cadquery as cq
from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.brep_to_h5m import (
    mesh_brep,
    mesh_to_h5m_in_memory_method,
)

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
    - h5m files can be used a transport geometry in DAGMC with OpenMC 
"""


def transport_particles_on_h5m_geometry(
    h5m_filename: str,
    material_tags: list,
    nuclides: list = None,
    cross_sections_xml: str = None,
):
    """A function for testing the geometry file with particle transport in
    DAGMC OpenMC. Requires openmc and either the cross_sections_xml to be
    specified. Returns the flux on each volume

    Arg:
        h5m_filename: The name of the DAGMC h5m file to test
        material_tags: The
        nuclides:
        cross_sections_xml:

    """

    import openmc
    from openmc.data import NATURAL_ABUNDANCE

    if nuclides is None:
        nuclides = list(NATURAL_ABUNDANCE.keys())

    materials = openmc.Materials()
    for i, material_tag in enumerate(material_tags):
        # simplified material definitions have been used to keen this example minimal
        mat_dag_material_tag = openmc.Material(name=material_tag)
        mat_dag_material_tag.add_nuclide(nuclides[i], 1, "ao")
        mat_dag_material_tag.set_density("g/cm3", 0.01)

        materials.append(mat_dag_material_tag)

    if cross_sections_xml:
        openmc.config["cross_sections"] = cross_sections_xml

    else:
        with open("cross_sections.xml", "w") as file:
            file.write(
                """
            <?xml version='1.0' encoding='UTF-8'?>
            <cross_sections>
            <library materials="H1" path="tests/ENDFB-7.1-NNDC_H1.h5" type="neutron"/>
            <library materials="H2" path="ENDFB-7.1-NNDC_H2.h5" type="neutron"/>
            </cross_sections>
            """
            )

        openmc.config["cross_sections"] = "cross_sections.xml"

    dag_univ = openmc.DAGMCUniverse(filename=h5m_filename)
    bound_dag_univ = dag_univ.bounded_universe()
    geometry = openmc.Geometry(root=bound_dag_univ)

    # initializes a new source object
    my_source = openmc.Source()

    center_of_geometry = (
        (dag_univ.bounding_box[0][0] + dag_univ.bounding_box[1][0]) / 2,
        (dag_univ.bounding_box[0][1] + dag_univ.bounding_box[1][1]) / 2,
        (dag_univ.bounding_box[0][2] + dag_univ.bounding_box[1][2]) / 2,
    )
    # sets the location of the source which is not on a vertex
    center_of_geometry_nudged = (
        center_of_geometry[0] + 0.1,
        center_of_geometry[1] + 0.1,
        center_of_geometry[2] + 0.1,
    )

    my_source.space = openmc.stats.Point(center_of_geometry_nudged)
    # sets the direction to isotropic
    my_source.angle = openmc.stats.Isotropic()
    # sets the energy distribution to 100% 14MeV neutrons
    my_source.energy = openmc.stats.Discrete([14e6], [1])

    # specifies the simulation computational intensity
    settings = openmc.Settings()
    settings.batches = 10
    settings.particles = 10000
    settings.inactive = 0
    settings.run_mode = "fixed source"
    settings.source = my_source

    # adds a tally to record the heat deposited in entire geometry
    cell_tally = openmc.Tally(name="flux")
    cell_tally.scores = ["flux"]

    # groups the two tallies
    tallies = openmc.Tallies([cell_tally])

    # builds the openmc model
    my_model = openmc.Model(
        materials=materials, geometry=geometry, settings=settings, tallies=tallies
    )

    # starts the simulation
    output_file = my_model.run()

    # loads up the output file from the simulation
    statepoint = openmc.StatePoint(output_file)

    my_flux_cell_tally = statepoint.get_tally(name="flux")

    return my_flux_cell_tally.mean.flatten()[0]


def test_transport_on_h5m_with_6_volumes():
    brep_object = "tests/test_brep_to_h5m/test_brep_file.brep"
    h5m_filename = "test_brep_file.h5m"
    volumes = 6
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_object=brep_object,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


def test_transport_on_h5m_with_1_volumes():
    result = cq.Workplane("front").box(2.0, 2.0, 0.5)

    volumes = 1
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    my_model = CadToDagmc()

    my_model.add_cadquery_object(
        result,
        material_tags=["mat1"],
    )

    my_model.export_dagmc_h5m_file(
        filename="cadquery_objects_and_stp_files.h5m", max_mesh_size=1, min_mesh_size=0.1
    )

    transport_particles_on_h5m_geometry(
        h5m_filename="one_cube.h5m",
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


def test_transport_on_h5m_with_2_joined_volumes():
    brep_object = "tests/test_brep_to_h5m/test_two_joined_cubes.brep"
    h5m_filename = "test_two_joined_cubes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_object=brep_object,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


def test_transport_on_h5m_with_2_sep_volumes():
    brep_object = "tests/test_brep_to_h5m/test_two_sep_cubes.brep"
    h5m_filename = "test_two_sep_cubes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_object=brep_object,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


def test_transport_result_h5m_with_2_sep_volumes():
    brep_object = "tests/test_brep_to_h5m/test_two_sep_cubes.brep"
    h5m_filename = "test_two_sep_cubes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    brep_to_h5m(
        brep_object=brep_object,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )

    new_tally = transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )

    brep_to_h5m(
        brep_object=brep_object,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
        min_mesh_size=30,
        max_mesh_size=50,
        mesh_algorithm=1,
    )
    stl_tally = transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )

    assert math.isclose(new_tally, stl_tally)


def test_stl_vs_in_memory_1_volume():
    brep_object = "tests/test_brep_to_h5m/one_cube.brep"
    volumes = 1
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    gmsh, volumes = mesh_brep(
        brep_object=brep_object,
        min_mesh_size=1,
        max_mesh_size=5,
        mesh_algorithm=1,
    )

    mesh_to_h5m_in_memory_method(
        volumes=volumes,
        material_tags=material_tags,
        h5m_filename="h5m_from_in_memory_method.h5m",
    )

    transport_particles_on_h5m_geometry(
        h5m_filename="h5m_from_in_memory_method.h5m",
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


def test_stl_vs_in_memory_2_joined_volume():
    brep_object = "tests/test_brep_to_h5m/test_two_joined_cubes.brep"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    gmsh, volumes = mesh_brep(
        brep_object=brep_object,
        min_mesh_size=1,
        max_mesh_size=5,
        mesh_algorithm=1,
    )

    mesh_to_h5m_in_memory_method(
        volumes=volumes,
        material_tags=material_tags,
        h5m_filename="h5m_from_in_memory_method.h5m",
    )

    transport_particles_on_h5m_geometry(
        h5m_filename="h5m_from_in_memory_method.h5m",
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )
