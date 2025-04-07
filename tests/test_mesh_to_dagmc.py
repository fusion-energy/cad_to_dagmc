from cad_to_dagmc import MeshToDagmc
import gmsh
from test_python_api import get_volumes_and_materials_from_h5m
from test_h5m_in_transport import transport_particles_on_h5m_geometry
import cadquery as cq
import assembly_mesh_plugin.plugin
import gmsh
from cad_to_dagmc import MeshToDagmc
import pydagmc
import math


def test_mesh_to_dagmc_with_mesh_object():
    gmsh.initialize()
    gmsh.open("tests/tagged_mesh.msh")

    mesh = MeshToDagmc()
    test_h5m_filename = "dagmc_from_gmsh_obj.h5m"
    mesh.export_gmsh_object_to_dagmc_h5m_file(filename=test_h5m_filename)
    gmsh.finalize()

    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat:shell",
        2: "mat:insert",
    }

    model = pydagmc.DAGModel(test_h5m_filename)
    v1 = model.volumes_by_id[1]  # get volume by id number 1
    v2 = model.volumes_by_id[2]  # get volume by id number 2
    assert len(model.volumes_by_id) == 2

    assert math.isclose(v1.volume, 102950.00006324494)
    assert math.isclose(v2.volume, 20000.0)
    assert v1.material == "shell"
    assert v2.material == "insert"

    transport_particles_on_h5m_geometry(
        h5m_filename="dagmc_from_gmsh_obj.h5m",
        material_tags=["shell", "insert"],
        nuclides=["H1", "H1"],
    )


def test_mesh_to_dagmc_with_cadquery_object():

    box_shape1 = cq.Workplane("XY").box(50, 50, 50)
    box_shape2 = cq.Workplane("XY").moveTo(0, 50).box(50, 50, 100)

    assembly = cq.Assembly()
    assembly.add(box_shape1, name="firstmat")
    assembly.add(box_shape2, name="aluminum")
    assembly.export("two_boxes.step")

    # getTaggedGmsh initializes gmsh and creates a mesh object ready for meshing
    mesh_object = assembly.getTaggedGmsh()
    mesh_object.model.mesh.generate(2)

    dagmc_model = MeshToDagmc(mesh_object)

    test_h5m_filename = "dagmc_from_gmsh_obj2.h5m"
    dagmc_model.export_gmsh_object_to_dagmc_h5m_file(filename=test_h5m_filename)

    # finalize the GMSH API after using export_gmsh_object_to_dagmc_h5m_file
    # and getTaggedGmsh as these both need access to the GMSH object.
    gmsh.finalize()

    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat:firstmat",
        2: "mat:aluminum",
    }
    model = pydagmc.DAGModel(test_h5m_filename)
    v1 = model.volumes_by_id[1]  # get volume by id number 1
    v2 = model.volumes_by_id[2]  # get volume by id number 2
    assert len(model.volumes_by_id) == 2

    assert math.isclose(v1.volume, 50 * 50 * 50)
    assert math.isclose(v2.volume, 50 * 50 * 100)
    assert v1.material == "firstmat"
    assert v2.material == "aluminum"

    transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["firstmat", "aluminum"],
        nuclides=["H1", "H1"],
    )
