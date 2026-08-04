from contextlib import contextmanager
from pathlib import Path
from typing import Iterable
import functools
import importlib.util
import cadquery as cq
import gmsh
import numpy as np
from cadquery import importers
from cadquery.occ_impl.importers.assembly import importStep as importStepAssembly
from cadquery.occ_impl.shapes import setThreads
from OCP.OSD import OSD_ThreadPool
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


class CadToDagmcMesherNotFoundError(ImportError):
    """Raised when cad-to-dagmc-mesher is not installed but its backend is requested."""

    def __init__(self, message=None):
        if message is None:
            message = (
                "cad-to-dagmc-mesher is not installed. It is not available on "
                "conda-forge so it cannot be included as a dependency of the "
                "cad-to-dagmc conda package.\n\n"
                "Install it with pip, which works alongside a conda installation:\n"
                "  pip install cad-to-dagmc-mesher\n\n"
                "Alternatively, use a meshing backend that is always available:\n"
                "  export_dagmc_h5m_file(..., meshing_backend='cadquery')\n"
                "  export_dagmc_h5m_file(..., meshing_backend='gmsh')"
            )
        super().__init__(message)


def _cad_to_dagmc_mesher_is_available() -> bool:
    """Return True when the cad-to-dagmc-mesher package can be imported."""
    return importlib.util.find_spec("cad_to_dagmc_mesher") is not None


def write_vtk(filename, vertices, tetrahedra):
    """Write a tetrahedral mesh to an ASCII VTK legacy file.

    The output is a pure tetrahedron UNSTRUCTURED_GRID in the same legacy
    format that gmsh writes today, so it can be read back with
    openmc.UnstructuredMesh(filename, library="moab"). The MOAB reader does
    not require the GLOBAL_ID POINT_DATA/CELL_DATA blocks that MOAB itself
    writes when it exports a mesh, so they are intentionally omitted. This
    was confirmed with a round trip transport test (see
    tests/test_write_vtk.py::test_write_vtk_openmc_moab_round_trip): a mesh
    written without GLOBAL_ID loads in MOAB and tallies identically to one
    written with it.

    Args:
        filename: Output file path.
        vertices: Sequence of [x, y, z] coordinates (list or numpy array).
        tetrahedra: Sequence of [v0, v1, v2, v3] zero-based vertex indices
            (list or numpy array).
    """
    n_tets = len(tetrahedra)
    # Stream the point/cell blocks with writelines() over generators. This
    # keeps memory bounded (nothing bigger than one line is materialised at a
    # time, matching the old per-line writes) while letting the C-level
    # writelines do the looping, which matters for the large meshes the mesher
    # can produce.
    with open(filename, "w") as f:
        f.write("# vtk DataFile Version 2.0\n")
        f.write("Unstructured mesh\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n")
        f.write(f"POINTS {len(vertices)} double\n")
        f.writelines(f"{v[0]} {v[1]} {v[2]}\n" for v in vertices)
        f.write(f"CELLS {n_tets} {n_tets * 5}\n")
        f.writelines(f"4 {t[0]} {t[1]} {t[2]} {t[3]}\n" for t in tetrahedra)
        f.write(f"CELL_TYPES {n_tets}\n")
        f.writelines("10\n" for _ in range(n_tets))


def combine_tet_meshes(tet_data):
    """Combine per-solid tetrahedral meshes into a single mesh.

    ``cad_to_dagmc_mesher.cad.mesh_assembly`` returns a ``tet_data`` dict
    mapping ``solid_id`` to ``{"vertices": (n, 3) array, "tetrahedra":
    (m, 4) array, ...}`` where each solid's tetrahedra index into that
    solid's own vertex list. To write a single unstructured grid the vertex
    arrays are concatenated and each solid's tetrahedra are offset by the
    running vertex count so they index into the combined vertex array.

    Args:
        tet_data: Mapping of solid_id -> dict with "vertices" and
            "tetrahedra" entries, as returned by mesh_assembly.

    Returns:
        (vertices, tetrahedra): a single (N, 3) float array of vertex
        coordinates and a single (M, 4) int array of zero-based tetrahedron
        vertex indices.
    """
    all_vertices = []
    all_tetrahedra = []
    offset = 0
    for solid_id in tet_data:
        verts = np.asarray(tet_data[solid_id]["vertices"], dtype=float).reshape(-1, 3)
        tets = np.asarray(tet_data[solid_id]["tetrahedra"], dtype=np.int64).reshape(-1, 4)
        all_vertices.append(verts)
        all_tetrahedra.append(tets + offset)
        offset += len(verts)

    if not all_vertices:
        return np.empty((0, 3), dtype=float), np.empty((0, 4), dtype=np.int64)

    return np.vstack(all_vertices), np.vstack(all_tetrahedra)


def resolve_imprint(imprint: bool | int) -> tuple[bool, int | None]:
    """Split the imprint argument into a flag and a thread limit.

    The imprint argument of the export methods accepts either a bool or an
    int. True imprints with however many threads the OpenCASCADE thread pool
    is set to (all cores unless the caller has already limited it), False
    skips imprinting, and a positive int imprints with that many threads.
    Imprinting runs in parallel and its peak RAM scales with the number of
    threads, so a large model that runs out of memory can often be imprinted
    by lowering the thread count.

    Args:
        imprint: the imprint argument as given by the user.

    Returns:
        (do_imprint, threads) where threads is None when the thread count is
        to be left as the caller set it.

    Raises:
        ValueError: if an int less than 1 is given.
        TypeError: if something other than a bool or an int is given.
    """
    # bool is a subclass of int so it has to be tested for first. It also
    # means an int cannot express "do not imprint": imprint=0 would be
    # indistinguishable from imprint=False, so 0 is rejected rather than
    # guessed at.
    if isinstance(imprint, bool):
        return imprint, None
    if isinstance(imprint, int):
        if imprint < 1:
            raise ValueError(
                f"imprint={imprint} is not a valid number of threads. Use "
                "imprint=False to skip imprinting, imprint=True to imprint "
                "with all available cores, or a positive int to imprint with "
                "that many threads."
            )
        return True, imprint
    raise TypeError(
        f"imprint must be a bool or an int, got {type(imprint).__name__}. Use "
        "imprint=True or imprint=False to turn imprinting on or off, or a "
        "positive int to imprint with that many threads."
    )


@contextmanager
def thread_limit(threads: int | None):
    """Limit the threads OpenCASCADE uses, restoring the limit afterwards.

    cadquery's setThreads sets the size of the OpenCASCADE thread pool that
    the boolean operations behind imprinting run on. The pool is process wide,
    so the previous size is put back on the way out and the cadquery
    operations that follow are left running on as many threads as before.

    Args:
        threads: the number of threads to allow, or None to leave the pool
            alone.
    """
    if threads is None:
        yield
        return

    previous = OSD_ThreadPool.DefaultPool_s().NbThreads()
    setThreads(threads)
    try:
        yield
    finally:
        setThreads(previous)


@contextmanager
def imprint_thread_limit(threads: int | None):
    """Limit the threads used by imprinting and by nothing else.

    The gmsh backend imprints through imprint_assembly, so there the imprint
    can simply be wrapped in thread_limit. The cadquery plugin and
    cad-to-dagmc-mesher instead imprint part way through their own meshing
    call, so wrapping that call would limit the meshing too, and the meshing
    is not what runs out of memory.

    Both of them reach the imprint through cq.occ_impl.assembly.imprint and
    look it up when they call it, so swapping in a wrapper that shrinks the
    pool around the real imprint keeps the limit on the imprint and off the
    meshing either side of it. The original function is put back on the way
    out, including when meshing raises part way through.

    Args:
        threads: the number of threads to imprint with, or None to leave the
            pool alone.
    """
    if threads is None:
        yield
        return

    real_imprint = cq.occ_impl.assembly.imprint

    # functools.wraps keeps the signature intact: imprint_assembly and
    # cad-to-dagmc-mesher both inspect it for the glue argument.
    @functools.wraps(real_imprint)
    def limited_imprint(*args, **kwargs):
        with thread_limit(threads):
            return real_imprint(*args, **kwargs)

    cq.occ_impl.assembly.imprint = limited_imprint
    try:
        yield
    finally:
        cq.occ_impl.assembly.imprint = real_imprint


def imprint_assembly(assembly, threads: int | None = None):
    """Imprint a CadQuery assembly into a connected compound.

    Uses the BOPAlgo_Builder based imprint with glue="partial" when the
    installed cadquery supports it (CadQuery/cadquery#2069, faster and
    lower RAM than the older BOPAlgo_MakeConnected based imprint, with the
    same result for touching, non-overlapping solids). Older cadquery
    versions fall back to the original single-argument imprint.

    Args:
        assembly: the cadquery assembly to imprint.
        threads: the number of threads to imprint with. Fewer threads lowers
            the peak RAM of the imprint at the cost of speed. Defaults to None
            which leaves the thread count as it is.

    Returns:
        (imprinted_shape, imprinted_solids_with_original_ids)
    """
    import inspect

    # Imprinting needs at least two solids to do anything. Skipping it for a
    # single solid is not just an optimization: the BOPAlgo_Builder based
    # imprint returns a Null shape when given fewer than two arguments.
    id_map = {}
    for obj, name, loc, _ in assembly:
        for solid in obj.moved(loc).Solids():
            id_map[solid] = name
    if len(id_map) < 2:
        solids = list(id_map)
        compound = cq.occ_impl.shapes.Compound.makeCompound(solids)
        return compound, {s: (id_map[s],) for s in solids}

    with thread_limit(threads):
        imprint = cq.occ_impl.assembly.imprint
        if "glue" in inspect.signature(imprint).parameters:
            return imprint(assembly, glue="partial")
        return imprint(assembly)


def share_coincident_face_ids(triangles_by_solid_by_face):
    """Give the face two touching solids share a single id in both of them.

    Imprinting leaves one face between two touching solids, but
    cadquery_direct_mesh_plugin numbers faces per solid, so depending on the
    installed version each solid can contribute its own id for that one face.
    Writing both produces two coincident one sided DAGMC surfaces instead of
    one surface carrying a sense for each volume, which does not transport
    correctly: particles crossing the interface are not handed to the
    neighbouring volume, and the flux tallied there comes out low with nothing
    reported.

    The plugin welds vertices across the whole assembly, so both copies of the
    interface index the same vertices and differ only in winding. Keying on the
    triangle set with each triangle sorted is therefore orientation insensitive
    and identifies the copies. Only the ids are rewritten. Each solid keeps its
    own winding under the shared id, which is what vertices_to_h5m expects: it
    writes the surface once from the first solid that refers to it and reads
    the second solid off the shared id to build GEOM_SENSE_2.

    Ids are handed out from 1 in order of first appearance rather than the
    plugin's original ids being kept. Merging without renumbering would leave
    the ids of the dropped copies unused, so the highest surface id would stay
    as high as the unmerged count. Those ids become DAGMC surface ids, and a
    DAGMC universe embedded in CSG shares an id space with the CSG surfaces, so
    an inflated range collides with them ("Surface ID 21 exists in both
    Universe 3 and the CSG geometry"). Renumbering also matches what gmsh and
    cad-to-dagmc-mesher produce.

    This reproduces what the plugin does when it shares imprinted face ids
    itself (jmwright/cadquery-direct-mesh-plugin#10), including the numbering.
    It is idempotent, so it is a no-op against a plugin that already shares
    them. Once that pull request is released AND the
    cadquery_direct_mesh_plugin floor in pyproject.toml is raised to that
    release, this function and its call can be removed. Removing it before the
    floor is raised would reintroduce the bug for anyone on an older plugin.

    Args:
        triangles_by_solid_by_face: Dict mapping solid_id -> face_id -> list of
            triangles, each triangle a list of vertex indices.

    Returns:
        The same mapping with coincident faces sharing one face id, and ids
        renumbered contiguously from 1.

    Raises:
        ValueError: if a face is shared by more than two solids, or if one
            solid carries the same face twice. Neither is representable as
            DAGMC geometry, and vertices_to_h5m would silently write a wrong
            sense rather than fail.
    """

    def canonical(triangles):
        return frozenset(tuple(sorted(int(vertex) for vertex in triangle))
                         for triangle in triangles)

    id_by_key = {}
    solid_ids_by_key = {}
    remapped = {}
    for solid_id, faces in triangles_by_solid_by_face.items():
        shared_faces = {}
        for triangles in faces.values():
            key = canonical(triangles)
            solid_ids_by_key.setdefault(key, []).append(solid_id)
            if key not in id_by_key:
                id_by_key[key] = len(id_by_key) + 1
            shared_faces[id_by_key[key]] = triangles
        remapped[solid_id] = shared_faces

    for key, solid_ids in solid_ids_by_key.items():
        if len(solid_ids) != len(set(solid_ids)):
            msg = (
                f"Solid {solid_ids[0]} has the same face twice, so it cannot be "
                "written as DAGMC geometry. This points at a degenerate or zero "
                "thickness feature in the CAD."
            )
            raise ValueError(msg)
        if len(solid_ids) > 2:
            msg = (
                f"The face with id {id_by_key[key]} is shared by solids "
                f"{sorted(solid_ids)}. A DAGMC surface separates at most two "
                "volumes, so this points at overlapping solids in the CAD."
            )
            raise ValueError(msg)

    return remapped


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

        # FACETING_TOLERANCE tag — stored on the root meshset via the
        # "global" dataset so DAGMC's GeomQueryTool reads a valid value.
        # Without this, DAGMC reads uninitialised memory and particle
        # tracking fails with lost particles at curved surface boundaries.
        ft_grp = tstt_tags.create_group("FACETING_TOLERANCE")
        ft_type = np.dtype("f8")
        ft_grp["type"] = ft_type
        ft_grp.attrs.create("class", 2, dtype=np.int32)
        # Compute a representative faceting tolerance from the mesh extent.
        _diag = np.linalg.norm(vertices_arr.max(axis=0) - vertices_arr.min(axis=0))
        _facet_tol = max(_diag * 1e-3, 1e-3)
        # MOAB's mhdf reader expects "default" and "global" as HDF5
        # datasets (not attributes).  Store them both ways for compat.
        ft_grp.create_dataset("default", data=np.array([_facet_tol], dtype=ft_type))
        ft_grp.create_dataset("global", data=np.array([_facet_tol], dtype=ft_type))
        # Also store as sparse tag data on root meshset (handle 0).
        ft_grp.create_dataset("id_list", data=np.array([0], dtype=np.uint64))
        ft_grp.create_dataset("values", data=np.array([_facet_tol], dtype=ft_type))

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
    # gmsh is a global singleton. If a previous session was left initialized
    # (for example by an export that errored part way through, or an earlier
    # call that did not finalize) then adding a new model here would leave the
    # stale models from that session alive, leaking memory and growing the
    # session on every call (see issue #187). Finalize any pre-existing
    # session first so we always start from a clean, single-model state.
    if gmsh.isInitialized():
        gmsh.finalize()
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add(f"made_with_cad_to_dagmc_package_{__version__}")
    return gmsh


def set_sizes_for_mesh(
    gmsh,
    min_mesh_size: float | None = None,
    max_mesh_size: float | None = None,
    mesh_algorithm: int = 1,
    set_size: dict[int | str, float] | None = None,
    original_set_size: dict[int | str, float] | None = None,
    threads: int = 0,
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
        threads: the number of threads for Gmsh to use. Passed into
            gmsh.option.setNumber("General.NumThreads", threads). 0 uses
            all available cores (default), 1 uses a single thread.

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
    gmsh.option.setNumber("General.NumThreads", threads)

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
                        # count solids in this child to repeat the tag appropriately                       
                        child_shape = child.toCompound() if hasattr(child, 'toCompound') else child.obj    
                        if child_shape is not None:                                                        
                            child_solids = child_shape.Solids() if hasattr(child_shape, 'Solids') else []  
                        else:                                                                              
                            child_solids = []                                                              
                        for _ in child_solids:                                                             
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
                    # count solids in this child to repeat the tag appropriately                           
                    child_shape = child.toCompound() if hasattr(child, 'toCompound') else child.obj        
                    if child_shape is not None:                                                            
                        child_solids = child_shape.Solids() if hasattr(child_shape, 'Solids') else []      
                    else:                                                                                  
                        child_solids = []  
                    # parts always have a name as cq will auto assign one
                    for _ in child_solids:                                                                 
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
        imprint: bool | int = True,
        set_size: dict[int | str, float] | None = None,
        volumes: Iterable[int] | None = None,
        threads: int = 0,
        meshing_backend: str | None = None,
        target_edge_length: float | None = None,
        tet_volumes: Iterable[str] | None = None,
        tolerance: float = 0.01,
        angular_tolerance: float = 0.2,
    ):
        """
        Exports an unstructured mesh file in VTK format for use with
        openmc.UnstructuredMesh. Compatible with the MOAB unstructured mesh
        library. Example useage openmc.UnstructuredMesh(filename="umesh.vtk",
        library="moab").

        The mesh can be produced either with gmsh or with the
        cad-to-dagmc-mesher backend. The gmsh backend uses the min/max mesh
        size and set_size arguments, while the cad-to-dagmc-mesher backend
        uses target_edge_length (and optionally tet_volumes) to control the
        tetrahedra. gmsh is used unless meshing_backend or one of the
        cad-to-dagmc-mesher specific arguments is provided.

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
                the geometry to cm for use in neutronics.
            imprint: whether to imprint the geometry or not. Defaults to True as this is
                normally needed to ensure the geometry is meshed correctly. However if
                you know your geometry does not need imprinting you can set this to False
                and this can save time. A positive int can be passed instead of True to
                imprint with that many threads, for example imprint=1 imprints on a
                single thread. Imprinting runs in parallel and its peak RAM scales with
                the number of threads, so fewer threads lowers the peak RAM of large
                models at the cost of speed. Only the imprint is limited, the meshing
                that follows it keeps all its threads whichever backend is used, and
                the thread count is restored afterwards so the cadquery operations
                that follow are unaffected.
            set_size: a dictionary mapping volume IDs (int) or material tag names
                (str) to target mesh sizes (floats). Material tags are resolved to
                all volume IDs that have that tag. Only used by the gmsh backend.
            volumes: a list of volume ids (int) to include in the mesh. If left
                as default (None) then all volumes will be included. Only used by
                the gmsh backend.
            threads: the number of threads for Gmsh to use. 0 uses all
                available cores (default), 1 uses a single thread.
            meshing_backend: the backend used to generate the tetrahedra, either
                "gmsh" or "cad-to-dagmc-mesher". If not set, the backend is
                auto-selected: "cad-to-dagmc-mesher" when target_edge_length or
                tet_volumes is provided, otherwise "gmsh".
            target_edge_length: the target tetrahedron edge length used by the
                cad-to-dagmc-mesher backend. Required when meshing_backend is
                "cad-to-dagmc-mesher".
            tet_volumes: an iterable of material tag names identifying which
                volumes to fill with tetrahedra when using the
                cad-to-dagmc-mesher backend. Defaults to all volumes.
            tolerance: linear deflection tolerance for the surface mesh, used by
                the cad-to-dagmc-mesher backend. This is in the units of the
                SCALED geometry, since scale_factor is applied before meshing,
                so scale it alongside scale_factor. With scale_factor=100 the
                0.01 default is a 0.1 mm deflection, which on a large model can
                produce a very fine mesh and exhaust memory. The same applies to
                min_mesh_size/max_mesh_size/set_size for the gmsh backend.
            angular_tolerance: angular deflection tolerance for the surface mesh,
                used by the cad-to-dagmc-mesher backend. An angle, so unaffected
                by scale_factor.


        Returns:
        --------
            filename : str
                The filename of the written unstructured mesh file.
        """

        # gmesh writes out a vtk file that is accepted by openmc.UnstructuredMesh
        # The library argument must be set to "moab"
        if Path(filename).suffix != ".vtk":
            raise ValueError("Unstructured mesh filename must have a .vtk extension")

        imprint, imprint_threads = resolve_imprint(imprint)

        if meshing_backend is None:
            # Auto-select the backend: the tet arguments are specific to
            # cad-to-dagmc-mesher, everything else defaults to gmsh.
            if target_edge_length is not None or tet_volumes is not None:
                meshing_backend = "cad-to-dagmc-mesher"
            else:
                meshing_backend = "gmsh"
        print(f"Using meshing backend: {meshing_backend}")

        if meshing_backend not in ("gmsh", "cad-to-dagmc-mesher"):
            raise ValueError(
                f'meshing_backend "{meshing_backend}" not supported. '
                'Available options are "gmsh" or "cad-to-dagmc-mesher"'
            )

        if meshing_backend == "cad-to-dagmc-mesher":
            return self._export_unstructured_mesh_file_with_mesher(
                filename=filename,
                target_edge_length=target_edge_length,
                tet_volumes=tet_volumes,
                tolerance=tolerance,
                angular_tolerance=angular_tolerance,
                imprint=imprint,
                imprint_threads=imprint_threads,
                scale_factor=scale_factor,
            )

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        if imprint:
            print("Imprinting assembly for unstructured mesh generation")
            imprinted_assembly, _ = imprint_assembly(assembly, threads=imprint_threads)
        else:
            imprinted_assembly = assembly

        # gmsh is a global singleton; finalize the session on every exit path
        # (including a mid-mesh exception) so repeated calls don't accumulate
        # models. gmsh_session_started is only set once init_gmsh() has bound
        # the local gmsh name, keeping the finally safe if init_gmsh() itself
        # raises. See issue #187.
        gmsh_session_started = False
        try:
            gmsh = init_gmsh()
            gmsh_session_started = True

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
                threads=threads,
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

            return filename
        finally:
            if gmsh_session_started and gmsh.isInitialized():
                gmsh.finalize()

    def _export_unstructured_mesh_file_with_mesher(
        self,
        filename: str,
        target_edge_length: float | None,
        tet_volumes: Iterable[str] | None,
        tolerance: float,
        angular_tolerance: float,
        imprint: bool,
        imprint_threads: int | None = None,
        scale_factor: float = 1.0,
    ) -> str:
        """Write an unstructured .vtk volume mesh using cad-to-dagmc-mesher.

        Meshes the assembly with cad-to-dagmc-mesher, combines the per-solid
        tetrahedra into a single mesh, and writes it as a legacy VTK file
        readable by openmc.UnstructuredMesh(filename, library="moab").
        """
        if target_edge_length is None:
            raise ValueError(
                "target_edge_length is required when meshing_backend is "
                '"cad-to-dagmc-mesher"'
            )

        assembly = _build_assembly(self.parts, scale_factor)

        # Default to tetrahedralising every volume. tet_volumes is matched
        # against material tags by the mesher, so pass the material tags.
        if tet_volumes is None:
            tet_volumes = list(self.material_tags)
        else:
            tet_volumes = list(tet_volumes)

        _, _, _, tet_data = _mesh_with_cad_to_dagmc_mesher(
            assembly=assembly,
            material_tags=self.material_tags,
            tolerance=tolerance,
            angular_tolerance=angular_tolerance,
            tet_volumes=tet_volumes,
            target_edge_length=target_edge_length,
            imprint=imprint,
            imprint_threads=imprint_threads,
        )

        if not tet_data:
            raise ValueError(
                "cad-to-dagmc-mesher produced no tetrahedra. Check that "
                "tet_volumes contains valid material tags and that "
                "target_edge_length is set."
            )

        tet_vertices, tetrahedra = combine_tet_meshes(tet_data)

        if Path(filename).parent:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

        write_vtk(filename, tet_vertices, tetrahedra)
        print(f"written unstructured mesh file {filename}")
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
        imprint: bool | int = True,
        set_size: dict[int | str, float] | None = None,
        threads: int = 0,
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
                and this can save time. A positive int can be passed instead of True to
                imprint with that many threads, for example imprint=1 imprints on a
                single thread. Imprinting runs in parallel and its peak RAM scales with
                the number of threads, so fewer threads lowers the peak RAM of large
                models at the cost of speed. The thread count is restored afterwards so
                the cadquery operations that follow are unaffected.
            set_size: a dictionary mapping volume IDs (int) or material tag names
                (str) to target mesh sizes (floats). Material tags are resolved to
                all volume IDs that have that tag.
            threads: the number of threads for Gmsh to use. 0 uses all
                available cores (default), 1 uses a single thread.
        """

        imprint, imprint_threads = resolve_imprint(imprint)

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        if imprint:
            print("Imprinting assembly for mesh generation")
            imprinted_assembly, _ = imprint_assembly(assembly, threads=imprint_threads)
        else:
            imprinted_assembly = assembly

        # gmsh is a global singleton; finalize the session on every exit path
        # (including a mid-mesh exception) so repeated calls don't accumulate
        # models. gmsh_session_started is only set once init_gmsh() has bound
        # the local gmsh name, keeping the finally safe if init_gmsh() itself
        # raises. See issue #187.
        gmsh_session_started = False
        try:
            gmsh = init_gmsh()
            gmsh_session_started = True

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
                threads=threads,
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
        finally:
            if gmsh_session_started and gmsh.isInitialized():
                gmsh.finalize()

    def export_dagmc_h5m_file(
        self,
        filename: str = "dagmc.h5m",
        implicit_complement_material_tag: str | None = None,
        scale_factor: float = 1.0,
        imprint: bool | int = True,
        **kwargs,
    ) -> str:
        """Saves a DAGMC h5m file of the geometry

        Args:
            filename: the filename to use for the saved DAGMC file.
            implicit_complement_material_tag: the name of the material tag to use
                for the implicit complement (void space).
            scale_factor: a scaling factor to apply to the geometry. All the
                linear mesh sizing arguments (min_mesh_size, max_mesh_size and
                set_size for gmsh, tolerance and target_edge_length for
                cad-to-dagmc-mesher, tolerance for cadquery) are in the units of
                the SCALED geometry, so the same number means the same thing on
                the output mesh whichever backend is used. For example with
                scale_factor=100 (m to cm) a tolerance of 0.5 is a 5 mm
                deflection. Note this means the defaults get finer as
                scale_factor grows: the cad-to-dagmc-mesher tolerance default of
                0.01 is a 0.1 mm deflection at scale_factor=100, which on a large
                model can produce a very fine mesh and exhaust memory, so scale
                the tolerance along with the geometry. angular_tolerance is an
                angle and so is unaffected by scaling.
            imprint: whether to imprint the geometry or not. A positive int can be
                passed instead of True to imprint with that many threads, for example
                imprint=1 imprints on a single thread. Imprinting runs in parallel and
                its peak RAM scales with the number of threads, so fewer threads lowers
                the peak RAM of large models at the cost of speed. Only the imprint is
                limited, the meshing that follows it keeps all its threads whichever
                backend is used, and the thread count is restored afterwards so the
                cadquery operations that follow are unaffected.

            **kwargs: Backend-specific parameters:

                Backend selection:
                - meshing_backend (str, optional): explicitly specify 'gmsh',
                  'cadquery' or 'cad-to-dagmc-mesher'. If not provided, backend is
                  auto-selected based on other arguments: tet_volumes or
                  target_edge_length select 'cad-to-dagmc-mesher', gmsh-specific
                  arguments select 'gmsh'. Defaults to 'cad-to-dagmc-mesher' if
                  no backend-specific arguments are given, falling back to
                  'cadquery' when cad-to-dagmc-mesher is not installed.
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
                - threads (int): number of threads for Gmsh to use. 0 uses all
                  available cores (default), 1 uses a single thread.

                For CadQuery backend:
                - tolerance (float): meshing tolerance (default: 0.1), in the
                  units of the scaled geometry (see scale_factor above)
                - angular_tolerance (float): angular tolerance (default: 0.1)

                For cad-to-dagmc-mesher backend:
                - tolerance (float): surface meshing tolerance (default: 0.01),
                  in the units of the scaled geometry (see scale_factor above).
                  With scale_factor=100 the 0.01 default is a 0.1 mm deflection,
                  which on a large model can produce a very fine mesh and
                  exhaust memory; scale the value with scale_factor.
                - angular_tolerance (float): surface angular tolerance (default: 0.2)
                - tet_volumes (Iterable[str]): material tag names of the volumes to
                  fill with tetrahedra for an unstructured volume mesh.
                - target_edge_length (float): target tetrahedron edge length. Both
                  tet_volumes and target_edge_length must be given together to write
                  a volume mesh; when they are, the return value is a
                  (dagmc_filename, umesh_filename) tuple.
                - umesh_filename (str): filename for the unstructured volume mesh
                  (default: 'umesh.vtk').

        Returns:
            str: the filename(s) for the files created.

        Raises:
            ValueError: If invalid parameter combinations are used.
        """

        imprint, imprint_threads = resolve_imprint(imprint)

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
            "threads",
        }
        cad_to_dagmc_mesher_keys = {"tolerance", "angular_tolerance", "tet_volumes", "target_edge_length"}
        all_acceptable_keys = cadquery_keys | gmsh_keys | cad_to_dagmc_mesher_keys | {"meshing_backend", "h5m_backend"}

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
            # Auto-select meshing_backend based on kwargs. tolerance and
            # angular_tolerance are accepted by both the cadquery and the
            # cad-to-dagmc-mesher backends, and when only those are given the
            # cad-to-dagmc-mesher backend is preferred.
            # umesh_filename is accepted by both the gmsh and the
            # cad-to-dagmc-mesher backends, so it is not gmsh specific, but it
            # is still part of gmsh_keys because it selects gmsh when nothing
            # else narrows the choice. Combining it with tolerance stays
            # ambiguous: the mesher only honours umesh_filename when
            # tet_volumes and target_edge_length are supplied too, so no single
            # backend accepts that combination as given.
            mesher_only_keys = {"tet_volumes", "target_edge_length"}
            gmsh_only_keys = gmsh_keys - {"umesh_filename"}
            has_cadquery = any(key in kwargs for key in cadquery_keys)
            has_gmsh = any(key in kwargs for key in gmsh_keys)
            has_mesher = any(key in kwargs for key in mesher_only_keys)
            if has_mesher:
                provided_gmsh = [key for key in sorted(gmsh_only_keys) if key in kwargs]
                if provided_gmsh:
                    provided_mesher = [
                        key for key in sorted(mesher_only_keys) if key in kwargs
                    ]
                    raise ValueError(
                        "Ambiguous backend: both cad-to-dagmc-mesher and GMSH-specific arguments provided.\n"
                        f"cad-to-dagmc-mesher-specific arguments: {sorted(mesher_only_keys)}\n"
                        f"GMSH-specific arguments: {sorted(gmsh_only_keys)}\n"
                        f"Provided cad-to-dagmc-mesher arguments: {provided_mesher}\n"
                        f"Provided GMSH arguments: {provided_gmsh}\n"
                        "Please provide only one backend's arguments."
                    )
                meshing_backend = "cad-to-dagmc-mesher"
            elif has_cadquery and has_gmsh:
                provided_cadquery = [key for key in sorted(cadquery_keys) if key in kwargs]
                provided_gmsh_only = [
                    key for key in sorted(gmsh_only_keys) if key in kwargs
                ]
                provided_gmsh_shared = [
                    key for key in sorted(gmsh_keys - gmsh_only_keys) if key in kwargs
                ]
                message = (
                    "Ambiguous backend: the arguments provided are not all accepted "
                    "by any single meshing backend.\n"
                    f"Accepted by cadquery and cad-to-dagmc-mesher: {provided_cadquery}\n"
                )
                if provided_gmsh_only:
                    message += f"Accepted by gmsh only: {provided_gmsh_only}\n"
                if provided_gmsh_shared:
                    message += (
                        "Accepted by gmsh and cad-to-dagmc-mesher: "
                        f"{provided_gmsh_shared}\n"
                        "Note that cad-to-dagmc-mesher only writes an unstructured "
                        "volume mesh when tet_volumes and target_edge_length are "
                        "also given.\n"
                    )
                message += "Please set meshing_backend explicitly."
                raise ValueError(message)
            elif has_cadquery:
                # cadquery_keys is a subset of cad_to_dagmc_mesher_keys, so
                # reaching here means only keys that both backends accept were
                # given and the choice is genuinely ambiguous. Prefer the
                # mesher and make the decision visible.
                provided_shared = [key for key in sorted(cadquery_keys) if key in kwargs]
                if not _cad_to_dagmc_mesher_is_available():
                    raise CadToDagmcMesherNotFoundError(
                        f"The arguments {provided_shared} are accepted by both the "
                        "cadquery and the cad-to-dagmc-mesher meshing backends, so "
                        "the cad-to-dagmc-mesher backend would be selected, but "
                        "cad-to-dagmc-mesher is not installed. It is not available "
                        "on conda-forge so it has to be installed separately.\n\n"
                        "Either install it:\n"
                        "  pip install cad-to-dagmc-mesher\n\n"
                        "or ask for the cadquery backend explicitly:\n"
                        f"  export_dagmc_h5m_file(..., meshing_backend='cadquery', "
                        f"{provided_shared[0]}=...)"
                    )
                warnings.warn(
                    f"The arguments {provided_shared} are accepted by both the "
                    "cadquery and the cad-to-dagmc-mesher meshing backends. The "
                    "cad-to-dagmc-mesher backend has been selected. Pass "
                    "meshing_backend='cadquery' or "
                    "meshing_backend='cad-to-dagmc-mesher' to choose explicitly."
                )
                meshing_backend = "cad-to-dagmc-mesher"
            elif has_gmsh:
                meshing_backend = "gmsh"
            elif _cad_to_dagmc_mesher_is_available():
                meshing_backend = "cad-to-dagmc-mesher"  # default
            else:
                # cad-to-dagmc-mesher is a dependency of the pip package but is
                # not on conda-forge, so a conda installation can be without it.
                # A call that names no backend at all has expressed no
                # preference, so fall back to cadquery, which is always present,
                # rather than failing. Warn so the substitution is visible and
                # so the remedy is to hand, since pip installing the mesher
                # works alongside a conda installation.
                warnings.warn(
                    "No meshing backend was given so the cad-to-dagmc-mesher "
                    "backend would be used, but cad-to-dagmc-mesher is not "
                    "installed. Falling back to the cadquery backend. "
                    "cad-to-dagmc-mesher is not available on conda-forge, "
                    "install it with pip, which works alongside a conda "
                    "installation:\n"
                    "  pip install cad-to-dagmc-mesher\n\n"
                    "Pass meshing_backend='cadquery' to select the cadquery "
                    "backend explicitly and silence this warning."
                )
                meshing_backend = "cadquery"

        # Validate meshing backend
        if meshing_backend not in ["gmsh", "cadquery", "cad-to-dagmc-mesher"]:
            raise ValueError(
                f'meshing_backend "{meshing_backend}" not supported. '
                'Available options are "gmsh", "cadquery", or "cad-to-dagmc-mesher"'
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
        threads = 0
        tet_data = None

        # Extract backend-specific parameters with defaults
        if meshing_backend == "cadquery":
            # CadQuery parameters
            tolerance = kwargs.get("tolerance", 0.1)
            angular_tolerance = kwargs.get("angular_tolerance", 0.1)

            if scale_factor != 1.0:
                # Transitional warning: tolerance used to be in unscaled units
                # for this backend only. Remove in a future release once the
                # consistent behaviour has been out for a while.
                warnings.warn(
                    f"tolerance ({tolerance}) is in the units of the scaled "
                    f"geometry, so with scale_factor={scale_factor} it is a "
                    f"deflection of {tolerance} in the output mesh's units. "
                    "This matches the gmsh and cad-to-dagmc-mesher backends. "
                    "Previous versions of cad_to_dagmc interpreted tolerance in "
                    "the units of the unscaled geometry for the cadquery "
                    "backend only, so this produces a mesh "
                    f"{scale_factor}x finer than before for the same tolerance; "
                    f"pass tolerance={tolerance * scale_factor} to reproduce the "
                    "old mesh density."
                )

            # Check for invalid parameters
            unstructured_volumes = kwargs.get("unstructured_volumes")
            if unstructured_volumes is not None or kwargs.get("tet_volumes") is not None:
                raise ValueError(
                    "CadQuery backend cannot be used for volume meshing. "
                    "unstructured_volumes and tet_volumes must be None when "
                    "using 'cadquery' backend."
                )

            # Warn about unused GMSH and cad-to-dagmc-mesher parameters
            gmsh_params = [
                "min_mesh_size",
                "max_mesh_size",
                "mesh_algorithm",
                "set_size",
                "umesh_filename",
                "method",
                "threads",
                "target_edge_length",
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
            threads = kwargs.get("threads", 0)

            # Warn about unused CadQuery and cad-to-dagmc-mesher parameters
            non_gmsh_params = [
                "tolerance",
                "angular_tolerance",
                "tet_volumes",
                "target_edge_length",
            ]
            unused_params = [param for param in non_gmsh_params if param in kwargs]
            if unused_params:
                warnings.warn(
                    f"The following parameters are ignored when using GMSH backend: "
                    f"{', '.join(unused_params)}"
                )

        elif meshing_backend == "cad-to-dagmc-mesher":
            tolerance = kwargs.get("tolerance", 0.01)
            angular_tolerance = kwargs.get("angular_tolerance", 0.2)

        assembly = cq.Assembly()
        for part in self.parts:
            assembly.add(part)

        original_ids = get_ids_from_assembly(assembly)

        # both id lists should be the same length as each other and the same
        # length as the self.material_tags
        if len(original_ids) != len(self.material_tags):
            msg = f"Number of volumes {len(original_ids)} is not equal to number of material tags {len(self.material_tags)}"
            raise ValueError(msg)

        # The gmsh backend opens a gmsh session (gmsh is a global singleton).
        # Wrap the whole meshing and export in try/finally so the session is
        # always finalized - on every return path and even if meshing raises
        # part way through. Without this, repeated calls accumulate gmsh models
        # in the session (see issue #187). gmsh_session_started is only set once
        # init_gmsh() has run, so the finally never touches the (function-local)
        # gmsh name before it is bound and never finalizes a session the caller
        # may own when using a non-gmsh backend.
        gmsh_session_started = False
        try:
            # Use the CadQuery direct mesh plugin
            if meshing_backend == "cadquery":
                import cadquery_direct_mesh_plugin
                # tolerance is documented as being in the units of the scaled
                # geometry, matching the gmsh and cad-to-dagmc-mesher backends
                # (both of which scale the geometry before meshing it). This
                # backend is the odd one out: the plugin tessellates the
                # unscaled solids and multiplies the resulting vertices by
                # scale_factor afterwards, so the tolerance it is given is in
                # unscaled units. Convert so the same number means the same
                # deflection on the output mesh whichever backend is used.
                cq_tolerance = tolerance / scale_factor
                # Mesh the assembly using CadQuery's direct-mesh plugin. The
                # plugin imprints internally, so the limit is put on the
                # imprint itself and the tessellation keeps all its threads.
                with imprint_thread_limit(imprint_threads):
                    cq_mesh = assembly.toMesh(
                        imprint=imprint,
                        tolerance=cq_tolerance,
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
                if imprint:
                    triangles_by_solid_by_face = share_coincident_face_ids(
                        triangles_by_solid_by_face
                    )
            # Use gmsh
            elif meshing_backend == "gmsh":
                # If assembly is not to be imprinted, pass through the assembly as-is
                if imprint:
                    print("Imprinting assembly for mesh generation")
                    imprinted_assembly, imprinted_solids_with_org_id = (
                        imprint_assembly(assembly, threads=imprint_threads)
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
                gmsh_session_started = True

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
                    threads=threads,
                )

                gmsh.model.mesh.generate(2)

                vertices, triangles_by_solid_by_face = mesh_to_vertices_and_triangles(
                    dims_and_vol_ids=volumes
                )

            elif meshing_backend == "cad-to-dagmc-mesher":
                tet_volumes_arg = kwargs.get("tet_volumes", kwargs.get("unstructured_volumes"))
                target_edge_length = kwargs.get("target_edge_length")
                umesh_filename = kwargs.get("umesh_filename", umesh_filename)

                # A volume (tet) mesh needs BOTH tet_volumes and
                # target_edge_length. Passing only one (or asking for a
                # umesh_filename without them) is a user error: fail fast with a
                # clear message rather than silently writing no .vtk and
                # returning a bare string instead of the (h5m, vtk) tuple.
                wants_umesh = (
                    bool(tet_volumes_arg)
                    or target_edge_length is not None
                    or "umesh_filename" in kwargs
                )
                if wants_umesh and not (tet_volumes_arg and target_edge_length):
                    raise ValueError(
                        "Writing an unstructured volume mesh with the "
                        "cad-to-dagmc-mesher backend requires BOTH tet_volumes "
                        "(material tag names) and target_edge_length. Got "
                        f"tet_volumes={tet_volumes_arg!r}, "
                        f"target_edge_length={target_edge_length!r}."
                    )

                # scale_factor is applied to the geometry before meshing so the
                # h5m and .vtk match the gmsh/cadquery backends (which scale).
                mesher_assembly = _build_assembly(self.parts, scale_factor)

                vertices, triangles_by_solid_by_face, material_tags_in_brep_order, tet_data = (
                    _mesh_with_cad_to_dagmc_mesher(
                        assembly=mesher_assembly,
                        material_tags=self.material_tags,
                        tolerance=tolerance,
                        angular_tolerance=angular_tolerance,
                        tet_volumes=tet_volumes_arg,
                        target_edge_length=target_edge_length,
                        imprint=imprint,
                        imprint_threads=imprint_threads,
                    )
                )

            else:
                raise ValueError(
                    f'meshing_backend {meshing_backend} not supported. '
                    'Available options are "cadquery", "gmsh", or "cad-to-dagmc-mesher"'
                )

            dagmc_filename = vertices_to_h5m(
                vertices=vertices,
                triangles_by_solid_by_face=triangles_by_solid_by_face,
                material_tags=material_tags_in_brep_order,
                h5m_filename=filename,
                implicit_complement_material_tag=implicit_complement_material_tag,
                method=h5m_backend,
            )

            if meshing_backend == "gmsh" and unstructured_volumes:
                # Resolve any material tag strings to volume IDs
                unstructured_volumes = resolve_unstructured_volumes(
                    unstructured_volumes, volumes, material_tags_in_brep_order
                )
                # remove all the unused occ volumes, this prevents them being meshed
                for volume_dim, volume_id in volumes:
                    if volume_id not in unstructured_volumes:
                        gmsh.model.occ.remove(
                            [(volume_dim, volume_id)], recursive=True
                        )
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

                return dagmc_filename, umesh_filename

            # The cad-to-dagmc-mesher backend produces the tetrahedra itself
            # (when tet_volumes + target_edge_length are given). Combine the
            # per-solid tet meshes and write a .vtk unstructured volume mesh
            # without going through gmsh. Keying on the user's request (both
            # tet args, guaranteed present together by the check above) rather
            # than on tet_data means a mesher that unexpectedly yields no tets
            # raises here instead of silently returning a bare string.
            if meshing_backend == "cad-to-dagmc-mesher" and tet_volumes_arg and target_edge_length:
                if not tet_data:
                    raise ValueError(
                        "cad-to-dagmc-mesher produced no tetrahedra despite "
                        f"tet_volumes={tet_volumes_arg!r} and "
                        f"target_edge_length={target_edge_length!r}. Check that "
                        "tet_volumes contains valid material tags."
                    )
                tet_vertices, tetrahedra = combine_tet_meshes(tet_data)
                if Path(umesh_filename).parent:
                    Path(umesh_filename).parent.mkdir(parents=True, exist_ok=True)
                write_vtk(umesh_filename, tet_vertices, tetrahedra)
                print(f"written unstructured mesh file {umesh_filename}")
                return dagmc_filename, umesh_filename

            return dagmc_filename
        finally:
            if gmsh_session_started and gmsh.isInitialized():
                gmsh.finalize()


def _build_assembly(parts, scale_factor: float = 1.0):
    """Build a CadQuery assembly from parts, optionally scaling each part.

    Shape.scale returns a new shape (it does not mutate in place), so the
    original parts in self.parts are left untouched and repeated exports stay
    consistent.
    """
    assembly = cq.Assembly()
    for part in parts:
        assembly.add(part.scale(scale_factor) if scale_factor != 1.0 else part)
    return assembly


def _mesh_with_cad_to_dagmc_mesher(
    assembly, material_tags, tolerance, angular_tolerance,
    tet_volumes, target_edge_length, imprint, imprint_threads=None,
):
    """Mesh using cad-to-dagmc-mesher and return vertices_to_h5m-compatible output.

    Returns ``(vertices, triangles_by_solid_by_face, material_tags,
    tet_data)`` where ``tet_data`` is the per-solid tetrahedral mesh dict
    (``{solid_id: {"vertices": ..., "tetrahedra": ..., ...}}``) or ``None``
    when no solids were volume-meshed. Volume meshing only happens when both
    ``tet_volumes`` and ``target_edge_length`` are supplied.
    """
    try:
        from cad_to_dagmc_mesher.cad import mesh_assembly
    except ImportError as e:
        raise CadToDagmcMesherNotFoundError() from e

    # The mesher imprints internally, so the limit is put on the imprint
    # itself and the meshing keeps all its threads.
    with imprint_thread_limit(imprint_threads):
        result = mesh_assembly(
            assembly,
            material_tags,
            tolerance=tolerance,
            angular_tolerance=angular_tolerance,
            tet_volumes=tet_volumes,
            target_edge_length=target_edge_length,
            imprint=imprint,
        )
    return (
        result["vertices"],
        result["triangles_by_solid_by_face"],
        result["material_tags"],
        result.get("tet_data"),
    )


def _get_all_leaf_children(assembly):
    """Recursively yield all leaf children (parts, not assemblies) from a CadQuery assembly."""
    for child in assembly.children:
        # If the child is itself an assembly, recurse
        if hasattr(child, "children") and len(child.children) > 0:
            yield from _get_all_leaf_children(child)
        else:
            yield child
