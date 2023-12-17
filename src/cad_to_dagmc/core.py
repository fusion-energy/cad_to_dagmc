import typing
from pathlib import Path

import cadquery as cq
import gmsh
import numpy as np
import OCP
import trimesh
from cadquery import importers
from pymoab import core, types


def fix_normals(vertices: typing.Sequence, triangles_in_each_volume: typing.Sequence):
    fixed_triangles = []
    for triangles in triangles_in_each_volume:
        fixed_triangles.append(fix_normal(vertices, triangles))
    return fixed_triangles


def fix_normal(vertices: typing.Sequence, triangles: typing.Sequence):
    mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)

    mesh.fix_normals()

    return mesh.faces


def define_moab_core_and_tags() -> typing.Tuple[core.Core, dict]:
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


def vertices_to_h5m(
    vertices: typing.Union[
        typing.Iterable[typing.Tuple[float, float, float]], typing.Iterable["cadquery.occ_impl.geom.Vector"]
    ],
    triangles_by_solid_by_face: typing.Iterable[typing.Iterable[typing.Tuple[int, int, int]]],
    material_tags: typing.Iterable[str],
    h5m_filename="dagmc.h5m",
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
    if (
        hasattr(vertices[0], "x")
        and hasattr(vertices[0], "y")
        and hasattr(vertices[0], "z")
    ):
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

    moab_core, tags = define_moab_core_and_tags()

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
                    sense_data = np.array(
                        [other_volume_set, volume_set], dtype="uint64"
                    )
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

    all_sets = moab_core.get_entities_by_handle(0)

    file_set = moab_core.create_meshset()

    moab_core.add_entities(file_set, all_sets)

    moab_core.write_file(h5m_filename)

    return h5m_filename


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
        The resulting gmsh object and volumes
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


def get_ids_from_assembly(assembly):
    ids = []
    for obj, name, loc, _ in assembly:
        ids.append(name)
    return ids


def get_ids_from_imprinted_assembly(solid_id_dict):
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


def merge_surfaces(parts):
    """Merges surfaces in the geometry that are the same. More details on
    the merging process in the DAGMC docs
    https://svalinn.github.io/DAGMC/usersguide/cubit_basics.html"""

    # solids = geometry.Solids()

    bldr = OCP.BOPAlgo.BOPAlgo_Splitter()

    if len(parts) == 1:
        # merged_solid = cq.Compound(solids)

        if isinstance(
            parts[0], (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)
        ):
            # stp file
            return parts[0], parts[0].wrapped
        else:
            return parts[0], parts[0].toOCC()

    # else:
    for solid in parts:
        # checks if solid is a compound as .val() is not needed for compounds
        if isinstance(solid, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            bldr.AddArgument(solid.wrapped)
        else:
            bldr.AddArgument(solid.val().wrapped)

    bldr.SetNonDestructive(True)

    bldr.Perform()

    bldr.Images()

    merged_solid = cq.Compound(bldr.Shape())

    return merged_solid, merged_solid.wrapped


class CadToDagmc:
    def __init__(self):
        self.parts = []
        self.material_tags = []

    def add_stp_file(
        self,
        filename: str,
        material_tags: typing.Iterable[str],
        scale_factor: float = 1.0,
    ):
        """Loads the parts from stp file into the model keeping track of the
        parts and their material tags.

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

        if scale_factor == 1:
            scaled_part = part
        else:
            scaled_part = part.scale(scale_factor)
        self.add_cadquery_object(object=scaled_part, material_tags=material_tags)

    def add_cadquery_object(
        self,
        object: typing.Union[
            cq.assembly.Assembly, cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid
        ],
        material_tags: typing.Iterable[str],
    ):
        """Loads the parts from CadQuery object into the model keeping track of
        the parts and their material tags.

        Args:
            object: the cadquery object to convert
            material_tags: the names of the DAGMC material tags to assign.
                These will need to be in the same order as the volumes in the
                STP file and match the material tags used in the neutronics
                code (e.g. OpenMC).
        """

        if isinstance(object, cq.assembly.Assembly):
            object = object.toCompound()

        if isinstance(object, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            iterable_solids = object.Solids()
        else:
            iterable_solids = object.val().Solids()
        self.parts = self.parts + iterable_solids

        if len(iterable_solids) != len(material_tags):
            msg = f"Number of volumes {len(iterable_solids)} is not equal to number of material tags {len(material_tags)}"
            raise ValueError(msg)

        for material_tag in material_tags:
            self.material_tags.append(material_tag)

    def export_dagmc_h5m_file(
        self,
        filename: str = "dagmc.h5m",
        min_mesh_size: float = 1,
        max_mesh_size: float = 5,
        mesh_algorithm: int = 1,
        msh_filename: str = None,
    ):
        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        (
            imprinted_assembly,
            imprinted_solids_with_original_id,
        ) = cq.occ_impl.assembly.imprint(assembly)

        gmsh, volumes = mesh_brep(
            brep_object=imprinted_assembly.wrapped._address(),
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
        )

        original_ids = get_ids_from_assembly(assembly)
        scrambled_ids = get_ids_from_imprinted_assembly(
            imprinted_solids_with_original_id
        )

        # both id lists should be the same length as each other and the same
        # length as the self.material_tags

        material_tags_in_brep_order = order_material_ids_by_brep_order(
            original_ids, scrambled_ids, self.material_tags
        )

        h5m_filename = mesh_to_h5m_in_memory_method(
            volumes=volumes,
            material_tags=material_tags_in_brep_order,
            h5m_filename=filename,
            msh_filename=msh_filename,
        )
        return h5m_filename
