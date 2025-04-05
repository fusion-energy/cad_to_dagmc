from cad_to_dagmc import MeshToDagmc
import gmsh
from test_python_api import get_volumes_and_materials_from_h5m
import cadquery as cq
import assembly_mesh_plugin.plugin
import gmsh
from cad_to_dagmc import MeshToDagmc

def test_mesh_to_dagmc_with_mesh_object():
    gmsh.initialize()
    gmsh.open("tests/tagged_mesh.msh")

    mesh = MeshToDagmc()
    test_h5m_filename = "dagmc_form_gmsh_obj.h5m"
    mesh.export_gmsh_object_to_dagmc_h5m_file(filename=test_h5m_filename)
    gmsh.finalize()

    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat:shell",
        2: "mat:insert",
    }

def test_mesh_to_dagmc_with_cadquery_object():

    box_shape1 = cq.Workplane("XY").box(50, 50, 50)
    box_shape2 = cq.Workplane("XY").moveTo(0,50).box(50, 50, 50)

    assembly = cq.Assembly()
    assembly.add(box_shape1, name="steel")
    assembly.add(box_shape2, name="aluminum")
    assembly.export("two_boxes.step")

    mesh_object = assembly.getTaggedGmsh()
    mesh_object.model.mesh.generate(2)

    dagmc_model = MeshToDagmc(mesh_object)
    dagmc_model.export_gmsh_object_to_dagmc_h5m_file(filename="dagmc_from_gmsh_obj2.h5m")