from cad_to_dagmc import MeshToDagmc
import gmsh


def test_mesh_to_dagmc_with_mesh_object():
    gmsh.initialize()
    gmsh.open("tests/tagged_mesh.msh")

    mesh = MeshToDagmc()
    mesh.export_gmsh_object_to_dagmc_h5m_file()
    gmsh.finalize()
