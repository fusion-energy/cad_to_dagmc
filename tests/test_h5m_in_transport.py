import pytest

try:
    import openmc
except ImportError:
    openmc = None

from cad_to_dagmc import CadToDagmc
import cadquery as cq

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
            </cross_sections>
            """
            )

        openmc.config["cross_sections"] = "cross_sections.xml"

    dag_univ = openmc.DAGMCUniverse(filename=h5m_filename)
    bound_dag_univ = dag_univ.bounded_universe()
    geometry = openmc.Geometry(root=bound_dag_univ)

    # initializes a new source object
    my_source = openmc.IndependentSource()

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
    settings.photon_transport = False

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


@pytest.mark.skipif(openmc is None, reason="openmc tests only required for CI")
def test_transport_result_h5m_with_2_sep_volumes():
    h5m_filename = "test_two_sep_volumes.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    workplane1 = cq.Workplane("XY").cylinder(height=10, radius=4)
    workplane2 = cq.Workplane("XY").moveTo(0, 15).cylinder(height=10, radius=5)
    # cq.Assembly().add(workplane1).add(workplane2)

    my_model = CadToDagmc()
    my_model.add_cadquery_object(workplane1, material_tags=[material_tags[0]])
    my_model.add_cadquery_object(workplane2, material_tags=[material_tags[1]])
    my_model.export_dagmc_h5m_file(filename=h5m_filename)

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


@pytest.mark.skipif(openmc is None, reason="openmc tests only required for CI")
def test_transport_result_h5m_with_1_curved_volumes():
    h5m_filename = "one_cylinder.h5m"
    volumes = 1
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    workplane1 = cq.Workplane("XY").cylinder(height=10, radius=4)

    my_model = CadToDagmc()
    my_model.add_cadquery_object(workplane1, material_tags=[material_tags[0]])
    my_model.export_dagmc_h5m_file(filename=h5m_filename)

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


@pytest.mark.skipif(openmc is None, reason="openmc tests only required for CI")
def test_transport_result_h5m_with_2_joined_curved_volumes():
    h5m_filename = "two_connected_cylinders.h5m"
    volumes = 2
    material_tags = [f"material_{n}" for n in range(1, volumes + 1)]

    workplane1 = cq.Workplane("XY").cylinder(height=10, radius=4)
    workplane2 = cq.Workplane("XY").cylinder(height=10, radius=5).cut(workplane1)

    my_model = CadToDagmc()
    my_model.add_cadquery_object(workplane1, material_tags=[material_tags[0]])
    my_model.add_cadquery_object(workplane2, material_tags=[material_tags[1]])
    my_model.export_dagmc_h5m_file(
        filename=h5m_filename,
    )

    transport_particles_on_h5m_geometry(
        h5m_filename=h5m_filename,
        material_tags=material_tags,
        nuclides=["H1"] * len(material_tags),
    )


@pytest.mark.skipif(openmc is None, reason="openmc tests only required for CI")
def test_h5m_with_single_volume_list():
    """The simplest geometry, a single 4 sided shape with lists instead of np arrays"""

    h5m_file = "tests/single_cube.h5m"

    my_model = CadToDagmc()
    my_model.add_stp_file(filename="tests/single_cube.stp", material_tags=["mat1"])
    my_model.export_dagmc_h5m_file(filename=h5m_file)

    h5m_files = [
        "tests/single_cube.h5m",
    ]

    for h5m_file in h5m_files:
        transport_particles_on_h5m_geometry(
            h5m_filename=h5m_file,
            material_tags=["mat1"],
            nuclides=["H1"],
        )


@pytest.mark.skipif(openmc is None, reason="openmc tests only required for CI")
def test_h5m_with_multi_volume_not_touching():

    h5m_file = "tests/two_disconnected_cubes.h5m"

    my_model = CadToDagmc()
    my_model.add_stp_file(
        filename="tests/two_disconnected_cubes.stp", material_tags=["mat1", "mat2"]
    )
    my_model.export_dagmc_h5m_file(filename=h5m_file)

    transport_particles_on_h5m_geometry(
        h5m_filename="tests/two_disconnected_cubes.h5m",
        material_tags=["mat1", "mat2"],
        nuclides=["H1", "H1"],
    )


@pytest.mark.skipif(openmc is None, reason="openmc tests only required for CI")
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
        my_model.add_stp_file(
            filename=stp_file,
            material_tags=mat_tags,
        )

        my_model.export_dagmc_h5m_file(filename=h5m_file)

        transport_particles_on_h5m_geometry(
            h5m_filename=h5m_file,
            material_tags=mat_tags,
            nuclides=["H1"] * len(mat_tags),
        )
