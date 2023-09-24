from typing import Iterable, Tuple, Union
import typing
import numpy as np
import trimesh
from pymoab import core, types


def fix_normals(vertices: list, triangles_in_each_volume: list):
    fixed_triangles = []
    for triangles in triangles_in_each_volume:
        fixed_triangles.append(fix_normal(vertices, triangles))
    return fixed_triangles


def fix_normal(vertices: list, triangles: list):
    mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)

    mesh.fix_normals()

    return mesh.faces


def _define_moab_core_and_tags() -> Tuple[core.Core, dict]:
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


def prepare_moab_core_volume_set(
    moab_core,
    volume_id,
    tags,
):
    volume_set = moab_core.create_meshset()

    # recent versions of MOAB handle this automatically
    # but best to go ahead and do it manually
    moab_core.tag_set_data(tags["global_id"], volume_set, volume_id)

    # set geom IDs
    moab_core.tag_set_data(tags["geom_dimension"], volume_set, 3)

    # set category tag values
    moab_core.tag_set_data(tags["category"], volume_set, "Volume")

    return moab_core, volume_set


def prepare_moab_core_surface_set(
    moab_core,
    surface_id,
    tags,
):
    surface_set = moab_core.create_meshset()

    moab_core.tag_set_data(tags["global_id"], surface_set, surface_id)

    # set geom IDs
    moab_core.tag_set_data(tags["geom_dimension"], surface_set, 2)

    # set category tag values
    moab_core.tag_set_data(tags["category"], surface_set, "Surface")

    return moab_core, surface_set


def add_triangles_to_moab_core(
    material_tag, surface_set, moab_core, tags, triangles, moab_verts, volume_set
):
    for triangle in triangles:
        tri = (
            moab_verts[int(triangle[0])],
            moab_verts[int(triangle[1])],
            moab_verts[int(triangle[2])],
        )

        moab_triangle = moab_core.create_element(types.MBTRI, tri)
        moab_core.add_entity(surface_set, moab_triangle)

    group_set = moab_core.create_meshset()

    moab_core.tag_set_data(tags["category"], group_set, "Group")

    moab_core.tag_set_data(tags["name"], group_set, f"mat:{material_tag}")

    moab_core.tag_set_data(tags["geom_dimension"], group_set, 4)

    moab_core.add_entity(group_set, volume_set)

    return moab_core


def vertices_to_h5m(
    vertices: Union[
        Iterable[Tuple[float, float, float]], Iterable["cadquery.occ_impl.geom.Vector"]
    ],
    triangles_by_solid_by_face: Iterable[Iterable[Tuple[int, int, int]]],
    material_tags: Iterable[str],
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
