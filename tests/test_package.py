from vertices_to_h5m import vertices_to_h5m
from pathlib import Path
import dagmc_h5m_file_inspector as di
import openmc
import openmc_data_downloader as odd
import math
import cad_to_dagmc

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
    - h5m files can be used a transport geometry in DAGMC with OpenMC
"""


from cadquery import importers
from OCP.GCPnts import GCPnts_QuasiUniformDeflection

# from cadquery.occ_impl import shapes
import OCP
import cadquery as cq
from vertices_to_h5m import vertices_to_h5m
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation


def transport_particles_on_h5m_geometry(
    h5m_filename,
    material_tags,
):
    """A function for testing the geometry file with particle transport in DAGMC OpenMC"""

    materials = openmc.Materials()
    for material_tag in material_tags:

        # simplified material definitions have been used to keen this example minimal
        mat_dag_material_tag = openmc.Material(name=material_tag)
        mat_dag_material_tag.add_nuclide("H1", 1, "ao")
        mat_dag_material_tag.set_density("g/cm3", 2)

        materials.append(mat_dag_material_tag)

    # downloads the nuclear data and sets the openmc_cross_sections environmental variable
    odd.just_in_time_library_generator(libraries="ENDFB-7.1-NNDC", materials=materials)

    # makes use of the dagmc geometry
    dag_univ = openmc.DAGMCUniverse(h5m_filename)

    # creates an edge of universe boundary surface
    vac_surf = openmc.Sphere(r=10000, surface_id=9999, boundary_type="vacuum")

    # specifies the region as below the universe boundary
    region = -vac_surf

    # creates a cell from the region and fills the cell with the dagmc geometry
    containing_cell = openmc.Cell(cell_id=9999, region=region, fill=dag_univ)

    geometry = openmc.Geometry(root=[containing_cell])

    # initialises a new source object
    my_source = openmc.Source()
    # sets the location of the source to x=0.1 y=0.1 z=0.1 which is not on a vertex
    my_source.space = openmc.stats.Point((0.1, 0.1, 0.1))
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
    cell_tally = openmc.Tally(name="heating")
    cell_tally.scores = ["heating"]

    # creates a mesh that covers the geometry
    mesh = openmc.RegularMesh()
    mesh.dimension = [100, 100, 100]
    mesh.lower_left = [
        -10,
        -10,
        -10,
    ]  # x,y,z coordinates start at 0 as this is a sector model
    mesh.upper_right = [10, 10, 10]

    # makes a mesh tally using the previously created mesh and records heating on the mesh
    mesh_tally = openmc.Tally(name="heating_on_mesh")
    mesh_filter = openmc.MeshFilter(mesh)
    mesh_tally.filters = [mesh_filter]
    mesh_tally.scores = ["heating"]

    # groups the two tallies
    tallies = openmc.Tallies([cell_tally, mesh_tally])

    # builds the openmc model
    my_model = openmc.Model(
        materials=materials, geometry=geometry, settings=settings, tallies=tallies
    )

    # starts the simulation
    my_model.run()


def test_h5m_production_with_single_volume_list():
    #     """The simplest geometry, a single 4 sided shape with lists instead of np arrays"""

    stp_files = ["tests/extrude_rectangle.stp", "tests/single_cube.stp"]
    for stp_file in stp_files:
        test_h5m_filename = "single_tet.h5m"

        stp_file = cad_to_dagmc.load_stp_file(stp_file)

        merged_stp_file = cad_to_dagmc.merge_surfaces(stp_file)
        vertices, triangles = cad_to_dagmc.tessellate(merged_stp_file, tolerance=2)

        vertices_to_h5m(
            vertices=vertices,
            triangles=[triangles],
            material_tags=["mat1"],
            h5m_filename=test_h5m_filename,
        )

        transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1"],
        )


def test_h5m_production_with_multi_volume_list():
    #     """The simplest geometry, a single 4 sided shape with lists instead of np arrays"""

    stp_files = [
        "tests/multi_volume_cylinders.stp",
        "tests/two_disconnected_cubes.stp",
        "tests/two_connected_cubes.stp",
    ]
    material_tags = [
        ["mat1", "mat2", "mat3", "mat4", "mat5", "mat6"],
        ["mat1", "mat2"],
        ["mat1", "mat2"],
    ]
    for stp_file, mat_tags in zip(stp_files, material_tags):

        stp_file_object = cad_to_dagmc.load_stp_file(stp_file)
        merged_stp_file = cad_to_dagmc.merge_surfaces(stp_file_object)
        vertices, triangles = cad_to_dagmc.tessellate_touching_parts(
            merged_stp_file, tolerance=2
        )

        vertices_to_h5m(
            vertices=vertices,
            triangles=triangles,
            material_tags=mat_tags,
            h5m_filename="test.h5m",
        )

        transport_particles_on_h5m_geometry(
            h5m_filename="test.h5m", material_tags=mat_tags
        )
