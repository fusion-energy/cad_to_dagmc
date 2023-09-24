import gmsh
from pathlib import Path
from .vertices_to_h5m import vertices_to_h5m
import typing


def mesh_brep(
    brep_object: str,
    min_mesh_size: float = 1,
    max_mesh_size: float = 10,
    mesh_algorithm: int = 1,
):
    """Creates a conformal surface meshes of the volumes in a Brep file using
    Gmsh.

    Args:
        brep_object: the filename of the Brep file to convert
        min_mesh_size: the minimum mesh element size to use in Gmsh. Passed
            into gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)
        max_mesh_size: the maximum mesh element size to use in Gmsh. Passed
            into gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)
        mesh_algorithm: The Gmsh mesh algorithm number to use. Passed into
            gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)

    Returns:
        The gmsh object and volumes in Brep file
    """

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add("made_with_brep_to_h5m_package")
    volumes = gmsh.model.occ.importShapesNativePointer(brep_object)
    # gmsh.model.occ.importShapes(brep_object)
    gmsh.model.occ.synchronize()

    gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
    gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)
    gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)
    gmsh.model.mesh.generate(2)

    return gmsh, volumes


def mesh_to_h5m_in_memory_method(
    volumes,
    material_tags: typing.Iterable[str],
    h5m_filename: str = "dagmc.h5m",
    msh_filename=None,
) -> str:
    """Converts gmsh volumes into a DAGMC h5m file.

    Args:
        volumes: the volumes in the gmsh file, found with gmsh.model.occ.importShapes
        material_tags: A list of material tags to tag the DAGMC volumes with.
            Should be in the same order as the volumes
        h5m_filename: the filename of the DAGMC h5m file to write

    Returns:
        The filename of the h5m file produced
    """

    if isinstance(material_tags, str):
        msg = f"material_tags should be a list of strings, not a single string."
        raise ValueError(msg)

    if len(volumes) != len(material_tags):
        msg = f"{len(volumes)} volumes found in Brep file is not equal to the number of material_tags {len(material_tags)} provided."
        raise ValueError(msg)

    n = 3  # number of verts in a triangles
    triangles_by_solid_by_face = {}
    for dim_and_vol in volumes:
        # removes all groups so that the following getEntitiesForPhysicalGroup
        # command only finds surfaces for the volume
        gmsh.model.removePhysicalGroups()

        vol_id = dim_and_vol[1]
        entities_in_volume = gmsh.model.getAdjacencies(3, vol_id)
        surfaces_in_volume = entities_in_volume[1]
        ps = gmsh.model.addPhysicalGroup(2, surfaces_in_volume)
        gmsh.model.setPhysicalName(2, ps, f"surfaces_on_volume_{vol_id}")

        groups = gmsh.model.getPhysicalGroups()
        group = groups[0]
        # for group in groups:
        dim = group[0]
        tag = group[1]

        surfaces = gmsh.model.getEntitiesForPhysicalGroup(dim, tag)

        # nodes_in_all_surfaces = []
        nodes_in_each_surface = {}
        for surface in surfaces:
            _, _, nodeTags = gmsh.model.mesh.getElements(2, surface)
            nodeTags = nodeTags[0].tolist()
            shifted_node_tags = []
            for nodeTag in nodeTags:
                shifted_node_tags.append(nodeTag - 1)
            grouped_node_tags = [
                shifted_node_tags[i : i + n]
                for i in range(0, len(shifted_node_tags), n)
            ]
            nodes_in_each_surface[surface] = grouped_node_tags
        triangles_by_solid_by_face[vol_id] = nodes_in_each_surface

    _, all_coords, _ = gmsh.model.mesh.getNodes()

    vertices = [all_coords[i : i + n].tolist() for i in range(0, len(all_coords), n)]

    if msh_filename is not None:
        gmsh.write(msh_filename)

    gmsh.finalize()

    # checks and fixes triangle fix_normals within vertices_to_h5m
    return vertices_to_h5m(
        vertices=vertices,
        triangles_by_solid_by_face=triangles_by_solid_by_face,
        material_tags=material_tags,
        h5m_filename=h5m_filename,
    )
