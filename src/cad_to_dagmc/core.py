from pathlib import Path
from typing import Iterable
import cadquery as cq
import gmsh
import numpy as np
from cadquery import importers
from cadquery.occ_impl.importers.assembly import importStep as importStepAssembly
import tempfile
import warnings
from typing import Iterable
from cad_to_dagmc import __version__


class PyMoabNotFoundError(ImportError):
    """Raised when pymoab is not installed but the pymoab backend is requested."""

    def __init__(self, message=None):
        if message is None:
            message = (
                "pymoab is not installed. pymoab/MOAB is not available on PyPI so it "
                "cannot be included as a dependency of cad-to-dagmc.\n\n"
                "You can install pymoab via one of these methods:\n"
                "  1. From conda-forge: conda install -c conda-forge moab\n"
                "  2. From extra index: pip install --extra-index-url https://shimwell.github.io/wheels moab\n"
                "  3. From source: https://bitbucket.org/fathomteam/moab\n\n"
                "Alternatively, use the h5py backend (the default) which does not require pymoab:\n"
                "  export_dagmc_h5m_file(..., h5m_backend='h5py')"
            )
        super().__init__(message)


def define_moab_core_and_tags():
    """Creates a MOAB Core instance which can be built up by adding sets of
    triangles to the instance

    Returns:
        (pymoab Core): A pymoab.core.Core() instance
        (pymoab tag_handle): A pymoab.core.tag_get_handle() instance
    """
    try:
        from pymoab import core, types
    except ImportError as e:
        raise PyMoabNotFoundError() from e

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
    vertices: list[tuple[float, float, float]] | list["cadquery.occ_impl.geom.Vector"],
    triangles_by_solid_by_face: dict[int, dict[int, list[list[int]]]],
    material_tags: list[str],
    h5m_filename: str = "dagmc.h5m",
    implicit_complement_material_tag: str | None = None,
    method: str = "h5py",
):
    """Converts vertices and triangle sets into a tagged h5m file compatible
    with DAGMC enabled neutronics simulations

    Args:
        vertices: List of vertex coordinates as (x, y, z) tuples or CadQuery vectors
        triangles_by_solid_by_face: Dict mapping solid_id -> face_id -> list of triangles
        material_tags: List of material tag names, one per solid
        h5m_filename: Output filename for the h5m file
        implicit_complement_material_tag: Optional material tag for implicit complement
        method: Backend to use for writing h5m file ('pymoab' or 'h5py')
    """
    if method == "pymoab":
        return _vertices_to_h5m_pymoab(
            vertices=vertices,
            triangles_by_solid_by_face=triangles_by_solid_by_face,
            material_tags=material_tags,
            h5m_filename=h5m_filename,
            implicit_complement_material_tag=implicit_complement_material_tag,
        )
    elif method == "h5py":
        return _vertices_to_h5m_h5py(
            vertices=vertices,
            triangles_by_solid_by_face=triangles_by_solid_by_face,
            material_tags=material_tags,
            h5m_filename=h5m_filename,
            implicit_complement_material_tag=implicit_complement_material_tag,
        )
    else:
        raise ValueError(f"method must be 'pymoab' or 'h5py', not '{method}'")


def _vertices_to_h5m_pymoab(
    vertices: list[tuple[float, float, float]] | list["cadquery.occ_impl.geom.Vector"],
    triangles_by_solid_by_face: dict[int, dict[int, list[list[int]]]],
    material_tags: list[str],
    h5m_filename: str = "dagmc.h5m",
    implicit_complement_material_tag: str | None = None,
):
    """PyMOAB backend for vertices_to_h5m."""
    try:
        from pymoab import types
    except ImportError as e:
        raise PyMoabNotFoundError() from e

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

    # Add the vertices once at the start
    all_moab_verts = moab_core.create_vertices(vertices)

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

                # Collect only the vertices that lie on triangles on this face
                face_vertices_set = set()
                for triangle in triangles_on_face:
                    face_vertices_set.update(triangle)
                face_vertices_list = sorted(face_vertices_set)

                # Only add these to the MOAB face
                moab_verts = [all_moab_verts[ii] for ii in face_vertices_list]
                moab_core.add_entity(face_set, moab_verts)

                for triangle in triangles_on_face:
                    tri = (
                        all_moab_verts[int(triangle[0])],
                        all_moab_verts[int(triangle[1])],
                        all_moab_verts[int(triangle[2])],
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

    # makes the folder if it does not exist
    if Path(h5m_filename).parent:
        Path(h5m_filename).parent.mkdir(parents=True, exist_ok=True)

    # moab_core.write_file only accepts strings
    if isinstance(h5m_filename, Path):
        moab_core.write_file(str(h5m_filename))
    else:
        moab_core.write_file(h5m_filename)

    print(f"written DAGMC file {h5m_filename}")

    return h5m_filename


def _vertices_to_h5m_h5py(
    vertices: list[tuple[float, float, float]] | list["cadquery.occ_impl.geom.Vector"],
    triangles_by_solid_by_face: dict[int, dict[int, list[list[int]]]],
    material_tags: list[str],
    h5m_filename: str = "dagmc.h5m",
    implicit_complement_material_tag: str | None = None,
):
    """H5PY backend for vertices_to_h5m.

    Creates an h5m file compatible with DAGMC using h5py directly,
    without requiring pymoab.
    """
    import h5py
    from datetime import datetime

    if len(material_tags) != len(triangles_by_solid_by_face):
        msg = f"The number of material_tags provided is {len(material_tags)} and the number of sets of triangles is {len(triangles_by_solid_by_face)}. You must provide one material_tag for every triangle set"
        raise ValueError(msg)

    # Convert CadQuery vectors to floats if needed
    if (
        hasattr(vertices[0], "x")
        and hasattr(vertices[0], "y")
        and hasattr(vertices[0], "z")
    ):
        vertices_floats = [(vert.x, vert.y, vert.z) for vert in vertices]
    else:
        vertices_floats = vertices

    # Build face_ids_with_solid_ids to track shared faces
    face_ids_with_solid_ids = {}
    for solid_id, triangles_on_each_face in triangles_by_solid_by_face.items():
        for face_id in triangles_on_each_face.keys():
            if face_id in face_ids_with_solid_ids:
                face_ids_with_solid_ids[face_id].append(solid_id)
            else:
                face_ids_with_solid_ids[face_id] = [solid_id]

    # Collect all unique faces and their triangles
    all_faces = {}  # face_id -> list of triangles
    for solid_id, triangles_on_each_face in triangles_by_solid_by_face.items():
        for face_id, triangles_on_face in triangles_on_each_face.items():
            if face_id not in all_faces:
                all_faces[face_id] = triangles_on_face

    # Convert vertices to numpy array
    vertices_arr = np.asarray(vertices_floats, dtype=np.float64)
    num_vertices = len(vertices_arr)

    # Collect all triangles
    all_triangles = []
    for face_id in sorted(all_faces.keys()):
        all_triangles.extend(all_faces[face_id])
    all_triangles = np.asarray(all_triangles, dtype=np.int64)
    num_triangles = len(all_triangles)

    # Create the h5m file
    # makes the folder if it does not exist
    if Path(h5m_filename).parent:
        Path(h5m_filename).parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(h5m_filename, "w") as f:
        tstt = f.create_group("tstt")

        # Global ID counter - starts at 1
        global_id = 1

        # === NODES ===
        nodes_group = tstt.create_group("nodes")
        coords = nodes_group.create_dataset("coordinates", data=vertices_arr)
        coords.attrs.create("start_id", global_id)
        global_id += num_vertices

        # Node tags
        node_tags = nodes_group.create_group("tags")
        node_tags.create_dataset("GLOBAL_ID", data=np.full(num_vertices, -1, dtype=np.int32))

        # === ELEMENTS ===
        elements = tstt.create_group("elements")

        # Element type enum
        elems = {
            "Edge": 1, "Tri": 2, "Quad": 3, "Polygon": 4, "Tet": 5,
            "Pyramid": 6, "Prism": 7, "Knife": 8, "Hex": 9, "Polyhedron": 10,
        }
        tstt["elemtypes"] = h5py.enum_dtype(elems)

        # History
        now = datetime.now()
        tstt.create_dataset(
            "history",
            data=[
                "cad_to_dagmc".encode("ascii"),
                __version__.encode("ascii"),
                now.strftime("%m/%d/%y").encode("ascii"),
                now.strftime("%H:%M:%S").encode("ascii"),
            ],
        )

        # Triangles
        tri3_group = elements.create_group("Tri3")
        tri3_group.attrs.create("element_type", elems["Tri"], dtype=tstt["elemtypes"])

        # Node indices are 1-based in h5m
        connectivity = tri3_group.create_dataset(
            "connectivity",
            data=all_triangles + 1,
            dtype=np.uint64,
        )
        triangle_start_id = global_id
        connectivity.attrs.create("start_id", triangle_start_id)
        global_id += num_triangles

        # Triangle tags
        tags_tri3 = tri3_group.create_group("tags")
        tags_tri3.create_dataset("GLOBAL_ID", data=np.full(num_triangles, -1, dtype=np.int32))

        # === SETS ===
        # Plan out the entity set structure:
        # For each solid: 1 volume set, N surface sets (one per face), 1 group set (material)
        # Plus: 1 file set at the end, optionally 1 implicit complement group

        solid_ids = list(triangles_by_solid_by_face.keys())
        num_solids = len(solid_ids)

        # Assign set IDs
        sets_start_id = global_id

        # Map solid_id -> volume_set_id
        volume_set_ids = {}
        # Map face_id -> surface_set_id
        surface_set_ids = {}
        # Map solid_id -> group_set_id
        group_set_ids = {}

        current_set_id = sets_start_id

        # First, assign IDs to all surfaces (one per unique face)
        for face_id in sorted(all_faces.keys()):
            surface_set_ids[face_id] = current_set_id
            current_set_id += 1

        # Then assign IDs to volumes
        for solid_id in solid_ids:
            volume_set_ids[solid_id] = current_set_id
            current_set_id += 1

        # Then assign IDs to groups (materials)
        for solid_id in solid_ids:
            group_set_ids[solid_id] = current_set_id
            current_set_id += 1

        # Implicit complement group (if requested)
        implicit_complement_set_id = None
        if implicit_complement_material_tag:
            implicit_complement_set_id = current_set_id
            current_set_id += 1

        # File set
        file_set_id = current_set_id
        current_set_id += 1

        global_id = current_set_id

        # === TAGS ===
        tstt_tags = tstt.create_group("tags")

        # Collect tagged set IDs for CATEGORY (all entities)
        # and GEOM_DIMENSION (only surfaces and volumes - not groups, to match pymoab)
        category_set_ids = []
        categories = []
        geom_dim_set_ids = []
        geom_dimensions = []

        # Volumes first (to match pymoab ordering)
        for solid_id in solid_ids:
            category_set_ids.append(volume_set_ids[solid_id])
            categories.append("Volume")
            geom_dim_set_ids.append(volume_set_ids[solid_id])
            geom_dimensions.append(3)

        # Groups (CATEGORY only - pymoab doesn't set geom_dimension on groups)
        # Note: Groups COULD have geom_dimension=4 set, but pymoab doesn't do this
        for solid_id in solid_ids:
            category_set_ids.append(group_set_ids[solid_id])
            categories.append("Group")

        # Surfaces
        for face_id in sorted(all_faces.keys()):
            category_set_ids.append(surface_set_ids[face_id])
            categories.append("Surface")
            geom_dim_set_ids.append(surface_set_ids[face_id])
            geom_dimensions.append(2)

        # Implicit complement (CATEGORY only)
        if implicit_complement_material_tag:
            category_set_ids.append(implicit_complement_set_id)
            categories.append("Group")

        # CATEGORY tag
        # Note: We use opaque dtype (|V32) to match pymoab output exactly.
        # A string dtype (|S32) would also work and be more readable in h5dump,
        # but we match pymoab for maximum compatibility.
        cat_group = tstt_tags.create_group("CATEGORY")
        cat_group.attrs.create("class", 1, dtype=np.int32)
        cat_group.create_dataset("id_list", data=np.array(category_set_ids, dtype=np.uint64))
        # Create opaque 32-byte type to match pymoab's H5T_OPAQUE
        opaque_dt = h5py.opaque_dtype(np.dtype("V32"))
        cat_group["type"] = opaque_dt
        # Encode category strings as 32-byte null-padded values
        cat_values = np.array([s.encode("ascii").ljust(32, b"\x00") for s in categories], dtype="V32")
        cat_group.create_dataset("values", data=cat_values)

        # GEOM_DIMENSION tag
        # Note: We only tag surfaces (dim=2) and volumes (dim=3), not groups.
        # Groups COULD have geom_dimension=4, but pymoab doesn't set this.
        geom_group = tstt_tags.create_group("GEOM_DIMENSION")
        geom_group["type"] = np.dtype("i4")
        geom_group.attrs.create("class", 1, dtype=np.int32)
        geom_group.attrs.create("default", -1, dtype=geom_group["type"])
        geom_group.attrs.create("global", -1, dtype=geom_group["type"])
        geom_group.create_dataset("id_list", data=np.array(geom_dim_set_ids, dtype=np.uint64))
        geom_group.create_dataset("values", data=np.array(geom_dimensions, dtype=np.int32))

        # GEOM_SENSE_2 tag (only for surfaces)
        surface_ids_list = [surface_set_ids[fid] for fid in sorted(all_faces.keys())]
        gs2_group = tstt_tags.create_group("GEOM_SENSE_2")
        gs2_dtype = np.dtype("(2,)u8")
        gs2_group["type"] = gs2_dtype
        gs2_group.attrs.create("class", 1, dtype=np.int32)
        gs2_group.attrs.create("is_handle", 1, dtype=np.int32)
        gs2_group.create_dataset("id_list", data=np.array(surface_ids_list, dtype=np.uint64))

        # Build sense data for each surface
        sense_values = []
        for face_id in sorted(all_faces.keys()):
            solids_for_face = face_ids_with_solid_ids[face_id]
            if len(solids_for_face) == 2:
                # Shared face - both volumes
                vol1 = volume_set_ids[solids_for_face[0]]
                vol2 = volume_set_ids[solids_for_face[1]]
                sense_values.append([vol1, vol2])
            else:
                # Single volume
                vol = volume_set_ids[solids_for_face[0]]
                sense_values.append([vol, 0])

        if sense_values:
            gs2_values = np.zeros((len(sense_values),), dtype=[("f0", "<u8", (2,))])
            gs2_values["f0"] = np.array(sense_values, dtype=np.uint64)
            gs2_space = h5py.h5s.create_simple((len(sense_values),))
            gs2_arr_type = h5py.h5t.array_create(h5py.h5t.NATIVE_UINT64, (2,))
            gs2_dset = h5py.h5d.create(gs2_group.id, b"values", gs2_arr_type, gs2_space)
            gs2_dset.write(h5py.h5s.ALL, h5py.h5s.ALL, gs2_values, mtype=gs2_arr_type)
            gs2_dset.close()

        # GLOBAL_ID tag - store as sparse tag with id_list and values
        # This stores the user-facing IDs for surfaces and volumes
        gid_ids = []
        gid_values = []
        # Surfaces get their face_id as global_id
        for face_id in sorted(all_faces.keys()):
            gid_ids.append(surface_set_ids[face_id])
            gid_values.append(face_id)
        # Volumes get their solid_id as global_id
        for solid_id in solid_ids:
            gid_ids.append(volume_set_ids[solid_id])
            gid_values.append(solid_id)
        # Groups also get the solid_id
        for solid_id in solid_ids:
            gid_ids.append(group_set_ids[solid_id])
            gid_values.append(solid_id)

        gid_group = tstt_tags.create_group("GLOBAL_ID")
        gid_group["type"] = np.dtype("i4")
        gid_group.attrs.create("class", 2, dtype=np.int32)
        gid_group.attrs.create("default", -1, dtype=gid_group["type"])
        gid_group.attrs.create("global", -1, dtype=gid_group["type"])
        gid_group.create_dataset("id_list", data=np.array(gid_ids, dtype=np.uint64))
        gid_group.create_dataset("values", data=np.array(gid_values, dtype=np.int32))

        # NAME tag (for groups - material names)
        name_ids = []
        name_values = []
        for solid_id, mat_tag in zip(solid_ids, material_tags):
            name_ids.append(group_set_ids[solid_id])
            name_values.append(f"mat:{mat_tag}")
        if implicit_complement_material_tag:
            name_ids.append(implicit_complement_set_id)
            name_values.append(f"mat:{implicit_complement_material_tag}_comp")

        name_group = tstt_tags.create_group("NAME")
        name_group.attrs.create("class", 1, dtype=np.int32)
        name_group.create_dataset("id_list", data=np.array(name_ids, dtype=np.uint64))
        name_group["type"] = h5py.opaque_dtype(np.dtype("S32"))
        name_group.create_dataset("values", data=name_values, dtype=name_group["type"])

        # Other standard tags (empty but needed)
        for tag_name in ["DIRICHLET_SET", "MATERIAL_SET", "NEUMANN_SET"]:
            tag_grp = tstt_tags.create_group(tag_name)
            tag_grp["type"] = np.dtype("i4")
            tag_grp.attrs.create("class", 1, dtype=np.int32)
            tag_grp.attrs.create("default", -1, dtype=tag_grp["type"])
            tag_grp.attrs.create("global", -1, dtype=tag_grp["type"])

        # === SETS structure ===
        sets_group = tstt.create_group("sets")

        # Build contents, parents, children, and list arrays
        contents = []
        list_rows = []
        parents_list = []
        children_list = []

        # Track triangle ranges per face
        tri_offset = 0
        face_triangle_ranges = {}
        for face_id in sorted(all_faces.keys()):
            tris = all_faces[face_id]
            face_triangle_ranges[face_id] = (tri_offset, len(tris))
            tri_offset += len(tris)

        # Track vertices per face
        face_vertex_sets = {}
        for face_id, tris in all_faces.items():
            verts = set()
            for tri in tris:
                verts.update(tri)
            face_vertex_sets[face_id] = sorted(verts)

        contents_end = -1
        children_end = -1
        parents_end = -1

        # Surface sets
        for face_id in sorted(all_faces.keys()):
            # Content: vertices + triangles for this face
            verts = face_vertex_sets[face_id]
            tri_start, tri_count = face_triangle_ranges[face_id]

            # Add individual vertex handles (1-based IDs)
            # Don't assume vertices are contiguous - store each one
            for v in verts:
                contents.append(v + 1)  # 1-based vertex ID

            # Add individual triangle handles
            for i in range(tri_count):
                contents.append(triangle_start_id + tri_start + i)

            contents_end = len(contents) - 1

            # Parent-child: surface is child of volume(s)
            solids_for_face = face_ids_with_solid_ids[face_id]
            for solid_id in solids_for_face:
                parents_list.append(volume_set_ids[solid_id])
            parents_end = len(parents_list) - 1

            # flags: 2 = MESHSET_SET (handles, not ranges)
            list_rows.append([contents_end, children_end, parents_end, 2])

        # Volume sets (empty contents, but have surface children)
        for solid_id in solid_ids:
            # Volumes have no direct content
            # Children are the surfaces
            faces_in_solid = list(triangles_by_solid_by_face[solid_id].keys())
            for face_id in faces_in_solid:
                children_list.append(surface_set_ids[face_id])
            children_end = len(children_list) - 1

            # flags: 2 = handle-based (0b0010)
            list_rows.append([contents_end, children_end, parents_end, 2])

        # Group sets (contain volume handles)
        for solid_id in solid_ids:
            contents.append(volume_set_ids[solid_id])
            contents_end = len(contents) - 1
            list_rows.append([contents_end, children_end, parents_end, 2])

        # Implicit complement group
        if implicit_complement_material_tag:
            # Add the last volume to the implicit complement group
            contents.append(volume_set_ids[solid_ids[-1]])
            contents_end = len(contents) - 1
            list_rows.append([contents_end, children_end, parents_end, 2])

        # File set (contains everything)
        contents.extend([1, file_set_id - 1])  # range of all entities
        contents_end = len(contents) - 1
        list_rows.append([contents_end, children_end, parents_end, 10])

        # Write sets datasets
        sets_group.create_dataset("contents", data=np.array(contents, dtype=np.uint64))
        if children_list:
            sets_group.create_dataset("children", data=np.array(children_list, dtype=np.uint64))
        else:
            sets_group.create_dataset("children", data=np.array([], dtype=np.uint64))
        if parents_list:
            sets_group.create_dataset("parents", data=np.array(parents_list, dtype=np.uint64))
        else:
            sets_group.create_dataset("parents", data=np.array([], dtype=np.uint64))

        lst = sets_group.create_dataset("list", data=np.array(list_rows, dtype=np.int64))
        lst.attrs.create("start_id", sets_start_id)

        # Set tags (GLOBAL_ID for each set)
        sets_tags = sets_group.create_group("tags")
        set_global_ids = []

        # Surface global IDs
        for face_id in sorted(all_faces.keys()):
            set_global_ids.append(face_id)

        # Volume global IDs
        for solid_id in solid_ids:
            set_global_ids.append(solid_id)

        # Group global IDs
        for solid_id in solid_ids:
            set_global_ids.append(solid_id)

        # Implicit complement
        if implicit_complement_material_tag:
            set_global_ids.append(-1)

        # File set
        set_global_ids.append(-1)

        sets_tags.create_dataset("GLOBAL_ID", data=np.array(set_global_ids, dtype=np.int32))

        # Max ID attribute
        tstt.attrs.create("max_id", np.uint64(global_id - 1))

    print(f"written DAGMC file {h5m_filename}")
    return h5m_filename


def get_volumes(gmsh, assembly, method="file", scale_factor=1.0):

    if method == "in memory":
        volumes = gmsh.model.occ.importShapesNativePointer(assembly.wrapped._address())

    elif method == "file":
        with tempfile.NamedTemporaryFile(suffix=".brep") as temp_file:
            if isinstance(assembly, cq.Assembly):
                assembly.toCompound().exportBrep(temp_file.name)
            else:
                assembly.exportBrep(temp_file.name)
            volumes = gmsh.model.occ.importShapes(temp_file.name)

    # updating the model to ensure the entities in the geometry are found
    gmsh.model.occ.synchronize()

    if scale_factor != 1.0:
        dim_tags = gmsh.model.getEntities(3)
        gmsh.model.occ.dilate(
            dim_tags, 0.0, 0.0, 0.0, scale_factor, scale_factor, scale_factor
        )
        # update the model to ensure the scaling factor has been applied
        gmsh.model.occ.synchronize()

    return gmsh, volumes


def init_gmsh():
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add(f"made_with_cad_to_dagmc_package_{__version__}")
    return gmsh


def set_sizes_for_mesh(
    gmsh,
    min_mesh_size: float | None = None,
    max_mesh_size: float | None = None,
    mesh_algorithm: int = 1,
    set_size: dict[int, float] | None = None,
    original_set_size: dict[int | str, float] | None = None,
):
    """Sets up the mesh sizes for each volume in the mesh.

    Args:
        occ_shape: the occ_shape of the Brep file to convert
        min_mesh_size: the minimum mesh element size to use in Gmsh. Passed
            into gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)
        max_mesh_size: the maximum mesh element size to use in Gmsh. Passed
            into gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)
        mesh_algorithm: The Gmsh mesh algorithm number to use. Passed into
            gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
        set_size: a dictionary of volume ids (int) and target mesh sizes
            (floats) to set for each volume, passed to gmsh.model.mesh.setSize.

    Returns:
        The resulting gmsh object and volumes
    """
    if min_mesh_size and max_mesh_size:
        if min_mesh_size > max_mesh_size:
            raise ValueError(
                f"min_mesh_size must be less than or equal to max_mesh_size. Currently min_mesh_size is set to {min_mesh_size} and max_mesh_size is set to {max_mesh_size}"
            )

    if min_mesh_size:
        gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)

    if max_mesh_size:
        gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)

    gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
    gmsh.option.setNumber("General.NumThreads", 0)  # Use all available cores

    if set_size:
        volumes = gmsh.model.getEntities(3)
        available_volumes = [volume[1] for volume in volumes]
        print("volumes", volumes)

        # Ensure all volume IDs in set_size exist in the available volumes
        for volume_id in set_size.keys():
            if volume_id not in available_volumes:
                raise ValueError(
                    f"volume ID of {volume_id} set in set_sizes but not found in available volumes {volumes}"
                )

        # Warn if any set_size values fall outside the global min/max range
        # Use original_set_size keys (which may be material tag strings) for
        # user-friendly warnings, falling back to resolved volume IDs
        warn_items = original_set_size.items() if original_set_size else set_size.items()
        for key, size in warn_items:
            if min_mesh_size is not None and size < min_mesh_size:
                warnings.warn(
                    f"set_size for {key} is {size} which is below "
                    f"min_mesh_size of {min_mesh_size}. The mesh size will be "
                    f"clamped to {min_mesh_size}. Try reducing min_mesh_size to "
                    f"encompass the set_size value."
                )
            if max_mesh_size is not None and size > max_mesh_size:
                warnings.warn(
                    f"set_size for {key} is {size} which is above "
                    f"max_mesh_size of {max_mesh_size}. The mesh size will be "
                    f"clamped to {max_mesh_size}. Try enlarging max_mesh_size to "
                    f"encompass the set_size value."
                )

        # Step 1: Preprocess boundaries to find the smallest size for shared surfaces
        boundary_sizes = {}  # Dictionary to store the minimum mesh size for each boundary
        for volume_id, size in set_size.items():
            boundaries = gmsh.model.getBoundary(
                [(3, volume_id)], recursive=True
            )  # dim must be set to 3
            print(f"Boundaries for volume {volume_id}: {boundaries}")

            for boundary in boundaries:
                boundary_key = (boundary[0], boundary[1])  # (dimension, tag)
                if boundary_key in boundary_sizes:
                    # If the boundary is already processed, keep the smaller size
                    boundary_sizes[boundary_key] = min(boundary_sizes[boundary_key], size)
                else:
                    boundary_sizes[boundary_key] = size

        # Step 2: Apply mesh sizes to all boundaries
        for boundary, size in boundary_sizes.items():
            gmsh.model.mesh.setSize([boundary], size)
            print(f"Set mesh size {size} for boundary {boundary}")

    return gmsh


def mesh_to_vertices_and_triangles(
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
        face_groups = gmsh.model.getPhysicalGroups(2)
        if face_groups:  # Only remove if 2D groups exist
            gmsh.model.removePhysicalGroups(face_groups)

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

    return vertices, triangles_by_solid_by_face


def get_ids_from_assembly(assembly: cq.assembly.Assembly):
    ids = []
    for obj, name, loc, _ in assembly:
        ids.append(name)
    return ids


def get_ids_from_imprinted_assembly(solid_id_dict):
    ids = []
    for id in list(solid_id_dict.values()):
        ids.append(id[0])
    return ids


def check_material_tags(material_tags, iterable_solids):
    if material_tags:
        if len(material_tags) != len(iterable_solids):
            msg = (
                "When setting material_tags the number of material_tags \n"
                "should be equal to the number of volumes in the CAD \n"
                f"geometry {len(iterable_solids)} volumes found in model \n"
                f"and {len(material_tags)} material_tags found"
            )
            raise ValueError(msg)
        for material_tag in material_tags:
            if not isinstance(material_tag, str):
                msg = f"material_tags should be an iterable of strings."
                raise ValueError(msg)
            if len(material_tag) > 28:
                msg = (
                    f"Material tag {material_tag} is too long. DAGMC will truncate this material tag "
                    f"to 28 characters. The resulting tag in the h5m file will be {material_tag[:28]}"
                )
                warnings.warn(msg)


def order_material_ids_by_brep_order(original_ids, scrambled_id, material_tags):
    material_tags_in_brep_order = []
    for brep_id in scrambled_id:
        id_of_solid_in_org = original_ids.index(brep_id)
        material_tags_in_brep_order.append(material_tags[id_of_solid_in_org])
    return material_tags_in_brep_order


def resolve_unstructured_volumes(
    unstructured_volumes: Iterable[int | str],
    volumes: list[tuple[int, int]],
    material_tags: list[str],
) -> list[int]:
    """Resolve a mixed list of volume IDs (int) and material tags (str) to volume IDs.

    Args:
        unstructured_volumes: An iterable containing volume IDs (int) or material tag
            names (str). Material tags are resolved to all volume IDs that have that tag.
        volumes: List of (dim, volume_id) tuples from GMSH, where the order corresponds
            to the order of material_tags.
        material_tags: List of material tags in the same order as volumes.

    Returns:
        A list of unique volume IDs (int) corresponding to the input.

    Raises:
        ValueError: If a material tag string is not found in material_tags.
        TypeError: If an element is neither int nor str.
    """
    resolved_ids = []

    # Build a mapping from material tag to volume IDs
    # volumes is a list of (dim, volume_id), and material_tags has the same order
    material_to_volume_ids: dict[str, list[int]] = {}
    for (_, volume_id), material_tag in zip(volumes, material_tags):
        if material_tag not in material_to_volume_ids:
            material_to_volume_ids[material_tag] = []
        material_to_volume_ids[material_tag].append(volume_id)

    for item in unstructured_volumes:
        if isinstance(item, int):
            resolved_ids.append(item)
        elif isinstance(item, str):
            if item not in material_to_volume_ids:
                available_tags = sorted(set(material_tags))
                raise ValueError(
                    f"Material tag '{item}' not found. "
                    f"Available material tags are: {available_tags}"
                )
            resolved_ids.extend(material_to_volume_ids[item])
        else:
            raise TypeError(
                f"unstructured_volumes must contain int (volume ID) or str (material tag), "
                f"got {type(item).__name__}"
            )

    # Remove duplicates while preserving order
    seen = set()
    unique_ids = []
    for vol_id in resolved_ids:
        if vol_id not in seen:
            seen.add(vol_id)
            unique_ids.append(vol_id)

    return unique_ids


def resolve_set_size(
    set_size: dict[int | str, float],
    volumes: list[tuple[int, int]],
    material_tags: list[str],
) -> dict[int, float]:
    """Resolve a set_size dict with int or str keys to int keys only.

    Args:
        set_size: A dictionary mapping volume IDs (int) or material tag names (str)
            to mesh sizes (float). Material tags are resolved to all volume IDs
            that have that tag.
        volumes: List of (dim, volume_id) tuples from GMSH, where the order corresponds
            to the order of material_tags.
        material_tags: List of material tags in the same order as volumes.

    Returns:
        A dictionary mapping volume IDs (int) to mesh sizes (float).

    Raises:
        ValueError: If a material tag string is not found in material_tags,
            or if a volume ID is specified multiple times with different sizes.
        TypeError: If a key is neither int nor str.
    """
    resolved: dict[int, float] = {}

    # Build a mapping from material tag to volume IDs
    material_to_volume_ids: dict[str, list[int]] = {}
    for (_, volume_id), material_tag in zip(volumes, material_tags):
        if material_tag not in material_to_volume_ids:
            material_to_volume_ids[material_tag] = []
        material_to_volume_ids[material_tag].append(volume_id)

    for key, size in set_size.items():
        if isinstance(key, int):
            volume_ids = [key]
        elif isinstance(key, str):
            if key not in material_to_volume_ids:
                available_tags = sorted(set(material_tags))
                raise ValueError(
                    f"Material tag '{key}' not found in set_size. "
                    f"Available material tags are: {available_tags}"
                )
            volume_ids = material_to_volume_ids[key]
        else:
            raise TypeError(
                f"set_size keys must be int (volume ID) or str (material tag), "
                f"got {type(key).__name__}"
            )

        for vol_id in volume_ids:
            if vol_id in resolved:
                if resolved[vol_id] != size:
                    raise ValueError(
                        f"Volume ID {vol_id} specified multiple times with different sizes: "
                        f"{resolved[vol_id]} and {size}. "
                        f"Each volume can only have one mesh size."
                    )
            else:
                resolved[vol_id] = size

    return resolved


def export_gmsh_object_to_dagmc_h5m_file(
    material_tags: list[str] | None = None,
    implicit_complement_material_tag: str | None = None,
    filename: str = "dagmc.h5m",
    h5m_backend: str = "h5py",
) -> str:
    """
    Exports a GMSH object to a DAGMC-compatible h5m file. Note gmsh should
    be initialized by the user prior and the gmsh model should be meshed before
    calling this. Also users should ensure that the gmsh model is finalized.

    Args:
        material_tags: A list of material tags corresponding to the volumes in the GMSH object.
        implicit_complement_material_tag: The material tag for the implicit complement (void space).
        filename: The name of the output h5m file. Defaults to "dagmc.h5m".
        h5m_backend: Backend for writing h5m file, 'pymoab' or 'h5py'. Defaults to 'h5py'.

    Returns:
        str: The filename of the generated DAGMC h5m file.

    Raises:
        ValueError: If the number of material tags does not match the number of volumes in the GMSH object.
    """

    if material_tags is None:
        material_tags = _get_material_tags_from_gmsh()

    dims_and_vol_ids = gmsh.model.getEntities(3)

    if len(dims_and_vol_ids) != len(material_tags):
        msg = f"Number of volumes {len(dims_and_vol_ids)} is not equal to number of material tags {len(material_tags)}"
        raise ValueError(msg)

    vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
        dims_and_vol_ids=dims_and_vol_ids
    )

    h5m_filename = vertices_to_h5m(
        vertices=vertices,
        triangles_by_solid_by_face=triangles_by_solid_by_face,
        material_tags=material_tags,
        h5m_filename=filename,
        implicit_complement_material_tag=implicit_complement_material_tag,
        method=h5m_backend,
    )

    return h5m_filename


def _get_material_tags_from_gmsh() -> list[str]:
    """Gets the Physical groups of 3D groups from the GMSH object and returns
    their names."""

    # Get all 3D physical groups (volumes)
    volume_groups = gmsh.model.getPhysicalGroups(3)

    material_tags = []
    # Get the name for each physical group
    for dim, tag in volume_groups:
        name = gmsh.model.getPhysicalName(dim, tag)
        material_tags.append(name)
        print(f"Material tag: {name}")
    print(f"Material tags: {material_tags}")
    return material_tags


def export_gmsh_file_to_dagmc_h5m_file(
    gmsh_filename: str,
    material_tags: list[str] | None = None,
    implicit_complement_material_tag: str | None = None,
    dagmc_filename: str = "dagmc.h5m",
    h5m_backend: str = "h5py",
) -> str:
    """Saves a DAGMC h5m file of the geometry GMsh file. This function
    initializes and finalizes Gmsh.

    Args:
        gmsh_filename (str): the filename of the GMSH mesh file.
        material_tags (list[str]): the names of the DAGMC
            material tags to assign. These will need to be in the same
            order as the volumes in the GMESH mesh and match the
            material tags used in the neutronics code (e.g. OpenMC).
        implicit_complement_material_tag (str | None, optional):
            the name of the material tag to use for the implicit
            complement (void space). Defaults to None which is a vacuum.
        dagmc_filename (str, optional): Output filename. Defaults to "dagmc.h5m".
        h5m_backend (str, optional): Backend for writing h5m file, 'pymoab' or 'h5py'.
            Defaults to 'h5py'.

    Returns:
        str: The filename of the generated DAGMC h5m file.

    Raises:
        ValueError: If the number of material tags does not match the number of volumes in the GMSH object.
    """

    gmsh.initialize()
    gmsh.open(gmsh_filename)

    if material_tags is None:
        material_tags = _get_material_tags_from_gmsh()

    dims_and_vol_ids = gmsh.model.getEntities(3)

    if len(dims_and_vol_ids) != len(material_tags):
        msg = f"Number of volumes {len(dims_and_vol_ids)} is not equal to number of material tags {len(material_tags)}"
        raise ValueError(msg)

    vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
        dims_and_vol_ids=dims_and_vol_ids
    )

    gmsh.finalize()

    h5m_filename = vertices_to_h5m(
        vertices=vertices,
        triangles_by_solid_by_face=triangles_by_solid_by_face,
        material_tags=material_tags,
        h5m_filename=dagmc_filename,
        implicit_complement_material_tag=implicit_complement_material_tag,
        method=h5m_backend,
    )

    return h5m_filename


class CadToDagmc:
    """Converts Step files and CadQuery parts to a DAGMC h5m file"""

    def __init__(self):
        self.parts = []
        self.material_tags = []

    def add_stp_file(
        self,
        filename: str,
        scale_factor: float = 1.0,
        material_tags: list[str] | str | None = None,
    ) -> int:
        """Loads the parts from stp file into the model.

        Args:
            filename: the filename used to save the html graph.
            material_tags: the names of the DAGMC material tags to assign.
                Can be a list of strings (one per volume), or one of the
                special strings "assembly_names" or "assembly_materials" to
                automatically extract tags from the STEP file's assembly
                structure (if the STEP file contains named parts or materials).
                When using a list, tags must be in the same order as the
                volumes in the geometry.
            scale_factor: a scaling factor to apply to the geometry that can be
                used to increase the size or decrease the size of the geometry.
                Useful when converting the geometry to cm for use in neutronics
                simulations.

        Returns:
            int: number of volumes in the stp file.
        """
        # If using assembly_names or assembly_materials, try to load as assembly
        if material_tags in ("assembly_names", "assembly_materials"):
            assembly = cq.Assembly()
            importStepAssembly(assembly, str(filename))
            if scale_factor != 1.0:
                # Scale each part in the assembly
                scaled_assembly = cq.Assembly()
                for child in assembly.children:
                    scaled_shape = child.obj.scale(scale_factor)
                    scaled_assembly.add(
                        scaled_shape,
                        name=child.name,
                        color=child.color,
                        loc=child.loc,
                    )
                    if hasattr(child, "material") and child.material is not None:
                        scaled_assembly.children[-1].material = child.material
                assembly = scaled_assembly
            return self.add_cadquery_object(
                cadquery_object=assembly, material_tags=material_tags
            )

        # Default behavior: load as compound/solid
        part = importers.importStep(str(filename)).val()

        if scale_factor == 1.0:
            scaled_part = part
        else:
            scaled_part = part.scale(scale_factor)
        return self.add_cadquery_object(
            cadquery_object=scaled_part, material_tags=material_tags
        )

    def add_cadquery_object(
        self,
        cadquery_object: (
            cq.assembly.Assembly
            | cq.occ_impl.shapes.Compound
            | cq.occ_impl.shapes.Solid
        ),
        material_tags: list[str] | str,
        scale_factor: float = 1.0,
    ) -> int:
        """Loads the parts from CadQuery object into the model.

        Args:
            cadquery_object: the cadquery object to convert, can be a CadQuery assembly
                cadquery workplane or a cadquery solid
            material_tags (Optional list[str]): the names of the
                DAGMC material tags to assign. These will need to be in the
                same order as the volumes in the geometry added (STP file and
                CadQuery objects) and match the material tags used in the
                neutronics code (e.g. OpenMC).
            scale_factor: a scaling factor to apply to the geometry that can be
                used to increase the size or decrease the size of the geometry.
                Useful when converting the geometry to cm for use in neutronics
                simulations.

        Returns:
            int: number of volumes in the stp file.
        """

        if isinstance(material_tags, str) and material_tags not in [
            "assembly_materials",
            "assembly_names",
        ]:
            raise ValueError(
                f"If material_tags is a string it must be 'assembly_materials' or 'assembly_names' but got {material_tags}"
            )

        if isinstance(cadquery_object, cq.assembly.Assembly):
            # look for materials in each part of the assembly
            if material_tags == "assembly_materials":
                material_tags = []
                for child in _get_all_leaf_children(cadquery_object):
                    if child.material is not None and child.material.name is not None:
                        material_tags.append(str(child.material.name))
                    else:
                        raise ValueError(
                            f"Not all parts in the assembly have materials assigned.\n"
                            f"When adding to an assembly include material=cadquery.Material('material_name')\n"
                            f"Missing material tag for child: {child}.\n"
                            "Please assign material tags to all parts or provide material_tags argument when adding the assembly.\n"
                        )
                print("material_tags found from assembly materials:", material_tags)
            elif material_tags == "assembly_names":
                material_tags = []
                for child in _get_all_leaf_children(cadquery_object):
                    # parts always have a name as cq will auto assign one
                    material_tags.append(child.name)
                print("material_tags found from assembly names:", material_tags)

            cadquery_compound = cadquery_object.toCompound()
        else:
            cadquery_compound = cadquery_object

        if isinstance(
            cadquery_compound, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)
        ):
            iterable_solids = cadquery_compound.Solids()
        else:
            iterable_solids = cadquery_compound.val().Solids()

        if scale_factor == 1.0:
            scaled_iterable_solids = iterable_solids
        else:
            scaled_iterable_solids = [
                part.scale(scale_factor) for part in iterable_solids
            ]

        check_material_tags(material_tags, scaled_iterable_solids)
        if material_tags:
            self.material_tags = self.material_tags + material_tags
        self.parts = self.parts + scaled_iterable_solids

        return len(scaled_iterable_solids)

    def export_unstructured_mesh_file(
        self,
        filename: str = "umesh.vtk",
        min_mesh_size: float = 1,
        max_mesh_size: float = 5,
        mesh_algorithm: int = 1,
        method: str = "file",
        scale_factor: float = 1.0,
        imprint: bool = True,
        set_size: dict[int | str, float] | None = None,
        volumes: Iterable[int] | None = None,
    ):
        """
        Exports an unstructured mesh file in VTK format for use with
        openmc.UnstructuredMesh. Compatible with the MOAB unstructured mesh
        library. Example useage openmc.UnstructuredMesh(filename="umesh.vtk",
        library="moab").

        Parameters:
        -----------
            filename : str, optional
                The name of the output file. Default is "umesh.vtk".
            min_mesh_size: the minimum mesh element size to use in Gmsh. Passed
                into gmsh.option.setNumber("Mesh.MeshSizeMin", min_mesh_size)
            max_mesh_size: the maximum mesh element size to use in Gmsh. Passed
                into gmsh.option.setNumber("Mesh.MeshSizeMax", max_mesh_size)
            mesh_algorithm: The Gmsh mesh algorithm number to use. Passed into
                gmsh.option.setNumber("Mesh.Algorithm", mesh_algorithm)
            method: the method to use to import the geometry into gmsh. Options
                are 'file' or 'in memory'. 'file' is the default and will write
                the geometry to a temporary file before importing it into gmsh.
                'in memory' will import the geometry directly into gmsh but
                requires the version of OpenCASCADE used to build gmsh to be
                the same as the version used by CadQuery. This is possible to
                ensure when installing the package with Conda but harder when
                installing from PyPI.
            scale_factor: a scaling factor to apply to the geometry that can be
                used to enlarge or shrink the geometry. Useful when converting
                Useful when converting the geometry to cm for use in neutronics
            imprint: whether to imprint the geometry or not. Defaults to True as this is
                normally needed to ensure the geometry is meshed correctly. However if
                you know your geometry does not need imprinting you can set this to False
                and this can save time.
            set_size: a dictionary mapping volume IDs (int) or material tag names
                (str) to target mesh sizes (floats). Material tags are resolved to
                all volume IDs that have that tag.
            volumes: a list of volume ids (int) to include in the mesh. If left
                as default (None) then all volumes will be included.


        Returns:
        --------
            gmsh : gmsh
                The gmsh object after finalizing the mesh.
        """

        # gmesh writes out a vtk file that is accepted by openmc.UnstructuredMesh
        # The library argument must be set to "moab"
        if Path(filename).suffix != ".vtk":
            raise ValueError("Unstructured mesh filename must have a .vtk extension")

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        if imprint:
            print("Imprinting assembly for unstructured mesh generation")
            imprinted_assembly, _ = cq.occ_impl.assembly.imprint(assembly)
        else:
            imprinted_assembly = assembly

        gmsh = init_gmsh()

        gmsh, volumes_in_model = get_volumes(
            gmsh, imprinted_assembly, method=method, scale_factor=scale_factor
        )

        # Resolve any material tag strings in set_size to volume IDs
        resolved_set_size = None
        if set_size:
            resolved_set_size = resolve_set_size(
                set_size, volumes_in_model, self.material_tags
            )

        gmsh = set_sizes_for_mesh(
            gmsh=gmsh,
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
            set_size=resolved_set_size,
            original_set_size=set_size,
        )

        if volumes:
            for volume_id in volumes_in_model:
                if volume_id[1] not in volumes:
                    gmsh.model.occ.remove([volume_id], recursive=True)
            gmsh.option.setNumber("Mesh.SaveAll", 1)
            gmsh.model.occ.synchronize()
            # Clear the mesh
            gmsh.model.mesh.clear()
            gmsh.option.setNumber(
                "Mesh.SaveElementTagType", 3
            )  # Save only volume elements

        gmsh.model.mesh.generate(3)

        # makes the folder if it does not exist
        if Path(filename).parent:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

        # gmsh.write only accepts strings
        if isinstance(filename, Path):
            gmsh.write(str(filename))
        else:
            gmsh.write(filename)

        gmsh.finalize()

        return filename

    def export_gmsh_mesh_file(
        self,
        filename: str = "mesh.msh",
        min_mesh_size: float | None = None,
        max_mesh_size: float | None = None,
        mesh_algorithm: int = 1,
        dimensions: int = 2,
        method: str = "file",
        scale_factor: float = 1.0,
        imprint: bool = True,
        set_size: dict[int | str, float] | None = None,
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
            method: the method to use to import the geometry into gmsh. Options
                are 'file' or 'in memory'. 'file' is the default and will write
                the geometry to a temporary file before importing it into gmsh.
                'in memory' will import the geometry directly into gmsh but
                requires the version of OpenCASCADE used to build gmsh to be
                the same as the version used by CadQuery. This is possible to
                ensure when installing the package with Conda but harder when
                installing from PyPI.
            scale_factor: a scaling factor to apply to the geometry that can be
                used to enlarge or shrink the geometry. Useful when converting
                Useful when converting the geometry to cm for use in neutronics
            imprint: whether to imprint the geometry or not. Defaults to True as this is
                normally needed to ensure the geometry is meshed correctly. However if
                you know your geometry does not need imprinting you can set this to False
                and this can save time.
            set_size: a dictionary mapping volume IDs (int) or material tag names
                (str) to target mesh sizes (floats). Material tags are resolved to
                all volume IDs that have that tag.
        """

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        if imprint:
            print("Imprinting assembly for mesh generation")
            imprinted_assembly, _ = cq.occ_impl.assembly.imprint(assembly)
        else:
            imprinted_assembly = assembly

        gmsh = init_gmsh()

        gmsh, volumes = get_volumes(
            gmsh, imprinted_assembly, method=method, scale_factor=scale_factor
        )

        # Resolve any material tag strings in set_size to volume IDs
        resolved_set_size = None
        if set_size:
            resolved_set_size = resolve_set_size(
                set_size, volumes, self.material_tags
            )

        gmsh = set_sizes_for_mesh(
            gmsh=gmsh,
            min_mesh_size=min_mesh_size,
            max_mesh_size=max_mesh_size,
            mesh_algorithm=mesh_algorithm,
            set_size=resolved_set_size,
            original_set_size=set_size,
        )

        gmsh.model.mesh.generate(dimensions)

        # makes the folder if it does not exist
        if Path(filename).parent:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

        # gmsh.write only accepts strings
        if isinstance(filename, Path):
            gmsh.write(str(filename))
        else:
            gmsh.write(filename)

        print(f"written GMSH mesh file {filename}")

        gmsh.finalize()

    def export_dagmc_h5m_file(
        self,
        filename: str = "dagmc.h5m",
        implicit_complement_material_tag: str | None = None,
        scale_factor: float = 1.0,
        imprint: bool = True,
        **kwargs,
    ) -> str:
        """Saves a DAGMC h5m file of the geometry

        Args:
            filename: the filename to use for the saved DAGMC file.
            implicit_complement_material_tag: the name of the material tag to use
                for the implicit complement (void space).
            scale_factor: a scaling factor to apply to the geometry.
            imprint: whether to imprint the geometry or not.

            **kwargs: Backend-specific parameters:

                Backend selection:
                - meshing_backend (str, optional): explicitly specify 'gmsh' or 'cadquery'.
                  If not provided, backend is auto-selected based on other arguments.
                  Defaults to 'cadquery' if no backend-specific arguments are given.
                - h5m_backend (str, optional): 'pymoab' or 'h5py' for writing h5m files.
                  Defaults to 'h5py'.

                For GMSH backend:
                - min_mesh_size (float): minimum mesh element size
                - max_mesh_size (float): maximum mesh element size
                - mesh_algorithm (int): GMSH mesh algorithm (default: 1)
                - method (str): import method 'file' or 'in memory' (default: 'file')
                - set_size (dict[int | str, float]): volume IDs (int) or material tag
                  names (str) mapped to target mesh sizes. Material tags are resolved
                  to all volume IDs that have that tag.
                - unstructured_volumes (Iterable[int | str]): volume IDs (int) or material
                  tag names (str) for unstructured mesh. Material tags are resolved to
                  all volume IDs that have that tag. Can mix ints and strings.
                - umesh_filename (str): filename for unstructured mesh (default: 'umesh.vtk')

                For CadQuery backend:
                - tolerance (float): meshing tolerance (default: 0.1)
                - angular_tolerance (float): angular tolerance (default: 0.1)

        Returns:
            str: the filename(s) for the files created.

        Raises:
            ValueError: If invalid parameter combinations are used.
        """

        # Define all acceptable kwargs
        cadquery_keys = {"tolerance", "angular_tolerance"}
        gmsh_keys = {
            "min_mesh_size",
            "max_mesh_size",
            "mesh_algorithm",
            "set_size",
            "umesh_filename",
            "method",
            "unstructured_volumes",
        }
        all_acceptable_keys = cadquery_keys | gmsh_keys | {"meshing_backend", "h5m_backend"}

        # Check for invalid kwargs
        invalid_keys = set(kwargs.keys()) - all_acceptable_keys
        if invalid_keys:
            raise ValueError(
                f"Invalid keyword arguments: {sorted(invalid_keys)}\n"
                f"Acceptable arguments are: {sorted(all_acceptable_keys)}"
            )

        # Handle meshing_backend - either from kwargs or auto-detect
        meshing_backend = kwargs.pop("meshing_backend", None)

        # Handle h5m_backend - pymoab or h5py
        h5m_backend = kwargs.pop("h5m_backend", "h5py")

        if meshing_backend is None:
            # Auto-select meshing_backend based on kwargs
            has_cadquery = any(key in kwargs for key in cadquery_keys)
            has_gmsh = any(key in kwargs for key in gmsh_keys)
            if has_cadquery and not has_gmsh:
                meshing_backend = "cadquery"
            elif has_gmsh and not has_cadquery:
                meshing_backend = "gmsh"
            elif has_cadquery and has_gmsh:
                provided_cadquery = [key for key in cadquery_keys if key in kwargs]
                provided_gmsh = [key for key in gmsh_keys if key in kwargs]
                raise ValueError(
                    "Ambiguous backend: both CadQuery and GMSH-specific arguments provided.\n"
                    f"CadQuery-specific arguments: {sorted(cadquery_keys)}\n"
                    f"GMSH-specific arguments: {sorted(gmsh_keys)}\n"
                    f"Provided CadQuery arguments: {provided_cadquery}\n"
                    f"Provided GMSH arguments: {provided_gmsh}\n"
                    "Please provide only one backend's arguments."
                )
            else:
                meshing_backend = "cadquery"  # default

        # Validate meshing backend
        if meshing_backend not in ["gmsh", "cadquery"]:
            raise ValueError(
                f'meshing_backend "{meshing_backend}" not supported. '
                'Available options are "gmsh" or "cadquery"'
            )

        print(f"Using meshing backend: {meshing_backend}")

        # Initialize variables to avoid unbound errors
        tolerance = 0.1
        angular_tolerance = 0.1
        min_mesh_size = None
        max_mesh_size = None
        mesh_algorithm = 1
        method = "file"
        set_size = None
        unstructured_volumes = None
        umesh_filename = "umesh.vtk"

        # Extract backend-specific parameters with defaults
        if meshing_backend == "cadquery":
            # CadQuery parameters
            tolerance = kwargs.get("tolerance", 0.1)
            angular_tolerance = kwargs.get("angular_tolerance", 0.1)

            # Check for invalid parameters
            unstructured_volumes = kwargs.get("unstructured_volumes")
            if unstructured_volumes is not None:
                raise ValueError(
                    "CadQuery backend cannot be used for volume meshing. "
                    "unstructured_volumes must be None when using 'cadquery' backend."
                )

            # Warn about unused GMSH parameters
            gmsh_params = [
                "min_mesh_size",
                "max_mesh_size",
                "mesh_algorithm",
                "set_size",
                "umesh_filename",
                "method",
            ]
            unused_params = [param for param in gmsh_params if param in kwargs]
            if unused_params:
                warnings.warn(
                    f"The following parameters are ignored when using CadQuery backend: "
                    f"{', '.join(unused_params)}"
                )

        elif meshing_backend == "gmsh":
            # GMSH parameters
            min_mesh_size = kwargs.get("min_mesh_size")
            max_mesh_size = kwargs.get("max_mesh_size")
            mesh_algorithm = kwargs.get("mesh_algorithm", 1)
            method = kwargs.get("method", "file")
            set_size = kwargs.get("set_size")
            unstructured_volumes = kwargs.get("unstructured_volumes")
            umesh_filename = kwargs.get("umesh_filename", "umesh.vtk")

            # Warn about unused CadQuery parameters
            cq_params = ["tolerance", "angular_tolerance"]
            unused_params = [param for param in cq_params if param in kwargs]
            if unused_params:
                warnings.warn(
                    f"The following parameters are ignored when using GMSH backend: "
                    f"{', '.join(unused_params)}"
                )

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        original_ids = get_ids_from_assembly(assembly)

        # both id lists should be the same length as each other and the same
        # length as the self.material_tags
        if len(original_ids) != len(self.material_tags):
            msg = f"Number of volumes {len(original_ids)} is not equal to number of material tags {len(self.material_tags)}"
            raise ValueError(msg)

        # Use the CadQuery direct mesh plugin
        if meshing_backend == "cadquery":
            import cadquery_direct_mesh_plugin
            # Mesh the assembly using CadQuery's direct-mesh plugin
            cq_mesh = assembly.toMesh(
                imprint=imprint,
                tolerance=tolerance,
                angular_tolerance=angular_tolerance,
                scale_factor=scale_factor,
            )

            # Fix the material tag order for imprinted assemblies
            if cq_mesh["imprinted_assembly"] is not None:
                imprinted_solids_with_org_id = cq_mesh[
                    "imprinted_solids_with_orginal_ids"
                ]

                scrambled_ids = get_ids_from_imprinted_assembly(
                    imprinted_solids_with_org_id
                )

                material_tags_in_brep_order = order_material_ids_by_brep_order(
                    original_ids, scrambled_ids, self.material_tags
                )
            else:
                material_tags_in_brep_order = self.material_tags

            check_material_tags(material_tags_in_brep_order, self.parts)

            # Extract the mesh information to allow export to h5m from the direct-mesh result
            vertices = cq_mesh["vertices"]
            triangles_by_solid_by_face = cq_mesh["solid_face_triangle_vertex_map"]
        # Use gmsh
        elif meshing_backend == "gmsh":
            # If assembly is not to be imprinted, pass through the assembly as-is
            if imprint:
                print("Imprinting assembly for mesh generation")
                imprinted_assembly, imprinted_solids_with_org_id = (
                    cq.occ_impl.assembly.imprint(assembly)
                )

                scrambled_ids = get_ids_from_imprinted_assembly(
                    imprinted_solids_with_org_id
                )

                material_tags_in_brep_order = order_material_ids_by_brep_order(
                    original_ids, scrambled_ids, self.material_tags
                )

            else:
                material_tags_in_brep_order = self.material_tags
                imprinted_assembly = assembly

            check_material_tags(material_tags_in_brep_order, self.parts)

            # Start generating the mesh
            gmsh = init_gmsh()

            gmsh, volumes = get_volumes(
                gmsh, imprinted_assembly, method=method, scale_factor=scale_factor
            )

            # Resolve any material tag strings in set_size to volume IDs
            resolved_set_size = None
            if set_size:
                resolved_set_size = resolve_set_size(
                    set_size, volumes, material_tags_in_brep_order
                )

            gmsh = set_sizes_for_mesh(
                gmsh=gmsh,
                min_mesh_size=min_mesh_size,
                max_mesh_size=max_mesh_size,
                mesh_algorithm=mesh_algorithm,
                set_size=resolved_set_size,
                original_set_size=set_size,
            )

            gmsh.model.mesh.generate(2)

            vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
                dims_and_vol_ids=volumes
            )

        else:
            raise ValueError(
                f'meshing_backend {meshing_backend} not supported. Available options are "cadquery" or "gmsh"'
            )

        dagmc_filename = vertices_to_h5m(
            vertices=vertices,
            triangles_by_solid_by_face=triangles_by_solid_by_face,
            material_tags=material_tags_in_brep_order,
            h5m_filename=filename,
            implicit_complement_material_tag=implicit_complement_material_tag,
            method=h5m_backend,
        )

        if unstructured_volumes:
            # Resolve any material tag strings to volume IDs
            unstructured_volumes = resolve_unstructured_volumes(
                unstructured_volumes, volumes, material_tags_in_brep_order
            )
            # remove all the unused occ volumes, this prevents them being meshed
            for volume_dim, volume_id in volumes:
                if volume_id not in unstructured_volumes:
                    gmsh.model.occ.remove([(volume_dim, volume_id)], recursive=True)
            gmsh.option.setNumber("Mesh.SaveAll", 1)
            gmsh.model.occ.synchronize()

            # removes all the 2D groups so that 2D faces are not included in the vtk file
            all_2d_groups = gmsh.model.getPhysicalGroups(2)
            for entry in all_2d_groups:
                gmsh.model.removePhysicalGroups([entry])

            gmsh.model.mesh.generate(3)
            gmsh.option.setNumber(
                "Mesh.SaveElementTagType", 3
            )  # Save only volume elements
            gmsh.write(umesh_filename)

            gmsh.finalize()

            return dagmc_filename, umesh_filename
        else:
            return dagmc_filename


def _get_all_leaf_children(assembly):
    """Recursively yield all leaf children (parts, not assemblies) from a CadQuery assembly."""
    for child in assembly.children:
        # If the child is itself an assembly, recurse
        if hasattr(child, "children") and len(child.children) > 0:
            yield from _get_all_leaf_children(child)
        else:
            yield child
