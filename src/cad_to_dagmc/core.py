import typing

import cadquery as cq
import gmsh
import numpy as np
from cadquery import importers
from pymoab import core, types


def _define_moab_core_and_tags() -> typing.Tuple[core.Core, dict]:
    """Creates a MOAB Core instance which can be built up by adding sets of
    triangles to the instance

    Returns:
        (pymoab Core): A pymoab.core.Core() instance
        (pymoab tag_handle): A pymoab.core.tag_get_handle() instance
    """

    # create pymoab instance
    moab_core = core.Core()

    tags = dict()

    sense_tag_name = "GEOM_SENSE_2"
    sense_tag_size = 2
    tags["surf_sense"] = moab_core.tag_get_handle(
        sense_tag_name,
        sense_tag_size,
        types.MB_TYPE_HANDLE,
        types.MB_TAG_SPARSE,
        create_if_missing=True,
    )

    tags["category"] = moab_core.tag_get_handle(
        types.CATEGORY_TAG_NAME,
        types.CATEGORY_TAG_SIZE,
        types.MB_TYPE_OPAQUE,
        types.MB_TAG_SPARSE,
        create_if_missing=True,
    )

    tags["name"] = moab_core.tag_get_handle(
        types.NAME_TAG_NAME,
        types.NAME_TAG_SIZE,
        types.MB_TYPE_OPAQUE,
        types.MB_TAG_SPARSE,
        create_if_missing=True,
    )

    tags["geom_dimension"] = moab_core.tag_get_handle(
        types.GEOM_DIMENSION_TAG_NAME,
        1,
        types.MB_TYPE_INTEGER,
        types.MB_TAG_DENSE,
        create_if_missing=True,
    )

    # Global ID is a default tag, just need the name to retrieve
    tags["global_id"] = moab_core.tag_get_handle(types.GLOBAL_ID_TAG_NAME)

    return moab_core, tags


def _vertices_to_h5m(
    vertices: typing.Union[
        typing.Iterable[typing.Tuple[float, float, float]],
        typing.Iterable["cadquery.occ_impl.geom.Vector"],
    ],
    triangles_by_solid_by_face: typing.Iterable[typing.Iterable[typing.Tuple[int, int, int]]],
    material_tags: typing.Iterable[str],
    h5m_filename="dagmc.h5m",
    implicit_complement_material_tag=None,
):
    """Converts vertices and triangle sets into a tagged h5m file compatible
    with DAGMC enabled neutronics simulations

    Args:
        vertices:
        triangles:
        material_tags:
        h5m_filename:
    """

    if len(material_tags) != len(triangles_by_solid_by_face):
        msg = f"The number of material_tags provided is {len(material_tags)} and the number of sets of triangles is {len(triangles_by_solid_by_face)}. You must provide one material_tag for every triangle set"
        raise ValueError(msg)

    # limited attribute checking to see if user passed in a list of CadQuery vectors
    if hasattr(vertices[0], "x") and hasattr(vertices[0], "y") and hasattr(vertices[0], "z"):
        vertices_floats = []
        for vert in vertices:
            vertices_floats.append((vert.x, vert.y, vert.z))
    else:
        vertices_floats = vertices

    face_ids_with_solid_ids = {}
    for solid_id, triangles_on_each_face in triangles_by_solid_by_face.items():
        for face_id, triangles_on_face in triangles_on_each_face.items():
            if face_id in face_ids_with_solid_ids.keys():
                face_ids_with_solid_ids[face_id].append(solid_id)
            else:
                face_ids_with_solid_ids[face_id] = [solid_id]

    moab_core, tags = _define_moab_core_and_tags()

    volume_sets_by_solid_id = {}
    for material_tag, (solid_id, triangles_on_each_face) in zip(
        material_tags, triangles_by_solid_by_face.items()
    ):
        volume_set = moab_core.create_meshset()
        volume_sets_by_solid_id[solid_id] = volume_set

    added_surfaces_ids = {}
    for material_tag, (solid_id, triangles_on_each_face) in zip(
        material_tags, triangles_by_solid_by_face.items()
    ):
        volume_set = volume_sets_by_solid_id[solid_id]

        moab_core.tag_set_data(tags["global_id"], volume_set, solid_id)
        moab_core.tag_set_data(tags["geom_dimension"], volume_set, 3)
        moab_core.tag_set_data(tags["category"], volume_set, "Volume")

        group_set = moab_core.create_meshset()
        moab_core.tag_set_data(tags["category"], group_set, "Group")
        moab_core.tag_set_data(tags["name"], group_set, f"mat:{material_tag}")
        moab_core.tag_set_data(tags["global_id"], group_set, solid_id)
        # moab_core.tag_set_data(tags["geom_dimension"], group_set, 4)

        for face_id, triangles_on_face in triangles_on_each_face.items():
            if face_id not in added_surfaces_ids.keys():
                face_set = moab_core.create_meshset()
                moab_core.tag_set_data(tags["global_id"], face_set, face_id)
                moab_core.tag_set_data(tags["geom_dimension"], face_set, 2)
                moab_core.tag_set_data(tags["category"], face_set, "Surface")

                if len(face_ids_with_solid_ids[face_id]) == 2:
                    other_solid_id = face_ids_with_solid_ids[face_id][1]
                    other_volume_set = volume_sets_by_solid_id[other_solid_id]
                    sense_data = np.array([other_volume_set, volume_set], dtype="uint64")
                else:
                    sense_data = np.array([volume_set, 0], dtype="uint64")

                moab_core.tag_set_data(tags["surf_sense"], face_set, sense_data)

                moab_verts = moab_core.create_vertices(vertices)
                moab_core.add_entity(face_set, moab_verts)

                for triangle in triangles_on_face:
                    tri = (
                        moab_verts[int(triangle[0])],
                        moab_verts[int(triangle[1])],
                        moab_verts[int(triangle[2])],
                    )

                    moab_triangle = moab_core.create_element(types.MBTRI, tri)
                    moab_core.add_entity(face_set, moab_triangle)

                added_surfaces_ids[face_id] = face_set
            else:
                face_set = added_surfaces_ids[face_id]

                other_solid_id = face_ids_with_solid_ids[face_id][0]

                other_volume_set = volume_sets_by_solid_id[other_solid_id]

                sense_data = np.array([other_volume_set, volume_set], dtype="uint64")
                moab_core.tag_set_data(tags["surf_sense"], face_set, sense_data)

            moab_core.add_parent_child(volume_set, face_set)

        moab_core.add_entity(group_set, volume_set)

    if implicit_complement_material_tag:
        group_set = moab_core.create_meshset()
        moab_core.tag_set_data(tags["category"], group_set, "Group")
        moab_core.tag_set_data(
            tags["name"], group_set, f"mat:{implicit_complement_material_tag}_comp"
        )
        moab_core.tag_set_data(tags["geom_dimension"], group_set, 4)
        moab_core.add_entity(
            group_set, volume_set
        )  # volume is arbitrary but should exist in moab core

    all_sets = moab_core.get_entities_by_handle(0)

    file_set = moab_core.create_meshset()

    moab_core.add_entities(file_set, all_sets)

    moab_core.write_file(h5m_filename)

    print(f"written DAGMC file {h5m_filename}")

    return h5m_filename


def _mesh_brep(
    brep_object: str,
    min_mesh_size: float = 1,
    max_mesh_size: float = 10,
    mesh_algorithm: int = 1,
    dimensions: int = 2,
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
        dimensions: The number of dimensions, 2 for a surface mesh 3 for a
            volume mesh. Passed to gmsh.model.mesh.generate()

    Returns:
        The resulting gmsh object and volumes
    """

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add("made_with_cad_to_dagmc_package")
    volumes = gmsh.model.occ.importShapesNativePointer(brep_object)
    gmsh.model.occ.synchronize()

    gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
    gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)
    gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)
    gmsh.model.mesh.generate(dimensions)

    return gmsh, volumes


def mesh_to_h5m_in_memory_method(
    dims_and_vol_ids,
):
    """Converts gmsh volumes into vertices and triangles for each face.

    Args:
        volumes: the volumes in the gmsh file, found with gmsh.model.occ.importShapes

    Returns:
        vertices and triangles (grouped by solid then by face)
    """

    n = 3  # number of verts in a triangles
    triangles_by_solid_by_face = {}
    for dim_and_vol in dims_and_vol_ids:
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
                shifted_node_tags[i : i + n] for i in range(0, len(shifted_node_tags), n)
            ]
            nodes_in_each_surface[surface] = grouped_node_tags
        triangles_by_solid_by_face[vol_id] = nodes_in_each_surface

    _, all_coords, _ = gmsh.model.mesh.getNodes()

    vertices = [all_coords[i : i + n].tolist() for i in range(0, len(all_coords), n)]

    return vertices, triangles_by_solid_by_face


def _get_ids_from_assembly(assembly: cq.assembly.Assembly):
    ids = []
    for obj, name, loc, _ in assembly:
        ids.append(name)
    return ids


def _get_ids_from_imprinted_assembly(solid_id_dict):
    ids = []
    for id in list(solid_id_dict.values()):
        ids.append(id[0])
    return ids


def order_material_ids_by_brep_order(original_ids, scrambled_id, material_tags):
    material_tags_in_brep_order = []
    for brep_id in scrambled_id:
        id_of_solid_in_org = original_ids.index(brep_id)
        material_tags_in_brep_order.append(material_tags[id_of_solid_in_org])
    return material_tags_in_brep_order


class MeshToDagmc:
    """Convert a GMSH mesh file to a DAGMC h5m file"""

    def __init__(self, filename: str):
        self.filename = filename

    def export_dagmc_h5m_file(
        self,
        material_tags: typing.Iterable[str],
        implicit_complement_material_tag: typing.Optional[str] = None,
        filename: str = "dagmc.h5m",
    ):
        """Saves a DAGMC h5m file of the geometry

        Args:
            material_tags (typing.Iterable[str]): the names of the DAGMC
                material tags to assign. These will need to be in the same
                order as the volumes in the GMESH mesh and match the
                material tags used in the neutronics code (e.g. OpenMC).
            implicit_complement_material_tag (typing.Optional[str], optional):
                the name of the material tag to use for the implicit
                complement (void space). Defaults to None which is a vacuum.
            filename (str, optional): _description_. Defaults to "dagmc.h5m".

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """

        gmsh.initialize()
        self.mesh_file = gmsh.open(self.filename)
        dims_and_vol_ids = gmsh.model.getEntities(3)

        if len(dims_and_vol_ids) != len(material_tags):
            msg = f"Number of volumes {len(dims_and_vol_ids)} is not equal to number of material tags {len(material_tags)}"
            raise ValueError(msg)

        vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
            dims_and_vol_ids=dims_and_vol_ids
        )

        gmsh.finalize()

        h5m_filename = _vertices_to_h5m(
            vertices=vertices,
            triangles_by_solid_by_face=triangles_by_solid_by_face,
            material_tags=material_tags,
            h5m_filename=filename,
            implicit_complement_material_tag=implicit_complement_material_tag,
        )

        return h5m_filename


class CadToDagmc:
    """Converts Step files and CadQuery parts to a DAGMC h5m file"""

    def __init__(self):
        self.parts = []

    def add_stp_file(
        self,
        filename: str,
        scale_factor: float = 1.0,
    ):
        """Loads the parts from stp file into the model.

        Args:
            filename: the filename used to save the html graph.
            material_tags: the names of the DAGMC material tags to assign.
                These will need to be in the same order as the volumes in the
                STP file and match the material tags used in the neutronics
                code (e.g. OpenMC).
            scale_factor: a scaling factor to apply to the geometry that can be
                used to increase the size or decrease the size of the geometry.
                Useful when converting the geometry to cm for use in neutronics
                simulations.
        """
        part = importers.importStep(str(filename)).val()

        if scale_factor == 1.0:
            scaled_part = part
        else:
            scaled_part = part.scale(scale_factor)
        self.add_cadquery_object(object=scaled_part)

    def add_cadquery_object(
        self,
        object: typing.Union[
            cq.assembly.Assembly, cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid
        ],
    ):
        """Loads the parts from CadQuery object into the model.

        Args:
            object: the cadquery object to convert
        """

        if isinstance(object, cq.assembly.Assembly):
            object = object.toCompound()

        if isinstance(object, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            iterable_solids = object.Solids()
        else:
            iterable_solids = object.val().Solids()
        self.parts = self.parts + iterable_solids

    def export_unstructured_mesh_file(
        self,
        filename: str = "umesh.h5m",
        min_mesh_size: float = 1,
        max_mesh_size: float = 5,
        mesh_algorithm: int = 1,
    ):

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        imprinted_assembly, _ = cq.occ_impl.assembly.imprint(assembly)

        gmsh, _ = _mesh_brep(
            brep_object=imprinted_assembly.wrapped._address(),
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
            dimensions=3,
        )

        # gmesh writes out a vtk file that is converted by pymoab into a h5 file
        gmsh.write(filename + ".vtk")

        moab_core = core.Core()
        moab_core.load_file(filename + ".vtk")
        moab_core.write_file(filename)

        gmsh.finalize()

        return gmsh

    def export_gmsh_mesh_file(
        self,
        filename: str = "mesh.msh",
        min_mesh_size: float = 1,
        max_mesh_size: float = 5,
        mesh_algorithm: int = 1,
        dimensions: int = 2,
    ):
        """Saves a GMesh msh file of the geometry in either 2D surface mesh or
        3D volume mesh.

        Args:
            filename
            min_mesh_size: the minimum size of mesh elements to use.
            max_mesh_size: the maximum size of mesh elements to use.
            mesh_algorithm: the gmsh mesh algorithm to use.
            dimensions: The number of dimensions, 2 for a surface mesh 3 for a
                volume mesh. Passed to gmsh.model.mesh.generate()
        """

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        imprinted_assembly, _ = cq.occ_impl.assembly.imprint(assembly)

        gmsh, _ = _mesh_brep(
            brep_object=imprinted_assembly.wrapped._address(),
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
            dimensions=dimensions,
        )

        gmsh.write(filename)

        print(f"written GMSH mesh file {filename}")

        gmsh.finalize()

    def export_dagmc_h5m_file(
        self,
        material_tags: typing.Iterable[str],
        filename: str = "dagmc.h5m",
        min_mesh_size: float = 1,
        max_mesh_size: float = 5,
        mesh_algorithm: int = 1,
        implicit_complement_material_tag: typing.Optional[str] = None,
    ) -> str:
        """Saves a DAGMC h5m file of the geometry

        Args:
            material_tags (typing.Iterable[str]): the names of the DAGMC
                material tags to assign. These will need to be in the
                same order as the volumes in the geometry added (STP
                file and CadQuery objects) and match the material tags
                used in the neutronics code (e.g. OpenMC).
            filename (str, optional): the filename to use for the saved DAGMC file. Defaults to "dagmc.h5m".
            min_mesh_size (float, optional): the minimum size of mesh elements to use. Defaults to 1.
            max_mesh_size (float, optional): the maximum size of mesh elements to use. Defaults to 5.
            mesh_algorithm (int, optional): the GMSH mesh algorithm to use.. Defaults to 1.
            implicit_complement_material_tag (typing.Optional[str], optional):
                the name of the material tag to use for the implicit complement
                (void space). Defaults to None which is a vacuum. Defaults to None.

        Returns:
            str: the DAGMC filename saved
        """

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        imprinted_assembly, imprinted_solids_with_org_id = cq.occ_impl.assembly.imprint(assembly)

        original_ids = _get_ids_from_assembly(assembly)
        scrambled_ids = _get_ids_from_imprinted_assembly(imprinted_solids_with_org_id)

        # both id lists should be the same length as each other and the same
        # length as the self.material_tags

        if len(original_ids) != len(material_tags):
            msg = f"Number of volumes {len(original_ids)} is not equal to number of material tags {len(material_tags)}"
            raise ValueError(msg)

        material_tags_in_brep_order = order_material_ids_by_brep_order(
            original_ids, scrambled_ids, material_tags
        )

        gmsh, volumes = _mesh_brep(
            brep_object=imprinted_assembly.wrapped._address(),  # in memory address
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
        )

        if isinstance(material_tags_in_brep_order, str):
            msg = f"material_tags should be a list of strings, not a single string."
            raise ValueError(msg)

        if len(volumes) != len(material_tags_in_brep_order):
            msg = f"{len(volumes)} volumes found in Brep file is not equal to the number of material_tags {len(material_tags_in_brep_order)} provided."
            raise ValueError(msg)

        dims_and_vol_ids = volumes

        vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
            dims_and_vol_ids=dims_and_vol_ids
        )

        gmsh.finalize()

        # checks and fixes triangle fix_normals within vertices_to_h5m
        return _vertices_to_h5m(
            vertices=vertices,
            triangles_by_solid_by_face=triangles_by_solid_by_face,
            material_tags=material_tags_in_brep_order,
            h5m_filename=filename,
            implicit_complement_material_tag=implicit_complement_material_tag,
        )
