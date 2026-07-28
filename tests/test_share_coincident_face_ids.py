"""Tests for sharing the face id of a face that two touching solids share.

cadquery_direct_mesh_plugin numbers faces per solid, so depending on the
installed version the one face between two touching solids can arrive as two
ids, one per solid. share_coincident_face_ids puts them back onto a single id
so the h5m gets one surface with a sense for each volume rather than two
coincident one sided surfaces.
"""

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import share_coincident_face_ids

# Two unit cubes touching on the plane x=1, meshed as two triangles per face
# over welded vertices. Face 4 of solid 1 and face 10 of solid 2 are the same
# face, wound in opposite directions.
TOUCHING_CUBES_SPLIT_IDS = {
    1: {
        1: [[0, 1, 2], [1, 3, 2]],
        4: [[4, 5, 6], [5, 7, 6]],
    },
    2: {
        7: [[8, 9, 10], [9, 11, 10]],
        10: [[6, 5, 4], [6, 7, 5]],
    },
}


def _two_touching_boxes():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 7, 0)).box(10, 4, 10))
    return assembly


def _surface_ids_and_shared_count(h5m_filename):
    """Return the surface global ids and how many surfaces bound two volumes."""
    from pymoab import core, types

    moab_core = core.Core()
    moab_core.load_file(str(h5m_filename))
    category_tag = moab_core.tag_get_handle(types.CATEGORY_TAG_NAME)
    global_id_tag = moab_core.tag_get_handle(types.GLOBAL_ID_TAG_NAME)

    surface_ids = []
    shared = 0
    for entity in moab_core.get_entities_by_type(
        moab_core.get_root_set(), types.MBENTITYSET
    ):
        try:
            category = moab_core.tag_get_data(category_tag, entity, flat=True)[0]
        except Exception:
            continue
        if isinstance(category, bytes):
            category = category.decode(errors="ignore")
        if category.split("\x00")[0] != "Surface":
            continue
        surface_ids.append(int(moab_core.tag_get_data(global_id_tag, entity, flat=True)[0]))
        if len(moab_core.get_parent_meshsets(entity)) == 2:
            shared += 1
    return sorted(surface_ids), shared


def test_coincident_faces_get_one_id():
    """The face both solids carry ends up under a single id."""
    shared = share_coincident_face_ids(TOUCHING_CUBES_SPLIT_IDS)

    assert set(shared[1]) & set(shared[2]), "no id is shared between the solids"
    assert len(set(shared[1]) | set(shared[2])) == 3, "expected 3 distinct faces"


def test_each_solid_keeps_its_own_winding():
    """Only ids are rewritten, the triangles are handed through untouched.

    vertices_to_h5m writes the surface from the first solid that refers to it,
    so the second solid's opposite winding must survive rather than be
    overwritten with a copy of the first.
    """
    shared = share_coincident_face_ids(TOUCHING_CUBES_SPLIT_IDS)
    shared_id = (set(shared[1]) & set(shared[2])).pop()

    assert shared[1][shared_id] == TOUCHING_CUBES_SPLIT_IDS[1][4]
    assert shared[2][shared_id] == TOUCHING_CUBES_SPLIT_IDS[2][10]


def test_is_idempotent():
    """A mapping that already shares ids is returned unchanged.

    This is what a plugin carrying jmwright/cadquery-direct-mesh-plugin#10
    produces, so the call has to be a no-op against it.
    """
    already_shared = share_coincident_face_ids(TOUCHING_CUBES_SPLIT_IDS)

    assert share_coincident_face_ids(already_shared) == already_shared


def test_face_shared_by_three_solids_raises():
    """A DAGMC surface separates at most two volumes."""
    face = [[0, 1, 2]]
    with pytest.raises(ValueError, match="shared by solids"):
        share_coincident_face_ids({1: {1: face}, 2: {2: face}, 3: {3: face}})


def test_same_face_twice_on_one_solid_raises():
    """A solid carrying the same face twice is degenerate geometry."""
    with pytest.raises(ValueError, match="same face twice"):
        share_coincident_face_ids({1: {1: [[0, 1, 2]], 2: [[2, 1, 0]]}})


def test_distinct_faces_keep_distinct_ids():
    """Faces that are not coincident are not merged."""
    separate = {1: {1: [[0, 1, 2]]}, 2: {2: [[3, 4, 5]]}}
    shared = share_coincident_face_ids(separate)

    assert not set(shared[1]) & set(shared[2])


def test_ids_are_contiguous_from_one():
    """Merging must not leave the dropped copies' ids unused.

    Face ids become DAGMC surface ids, and a DAGMC universe embedded in CSG
    shares an id space with the CSG surfaces, so an id range inflated by gaps
    collides with them. Renumbering keeps the range as small as the surface
    count.
    """
    shared = share_coincident_face_ids(TOUCHING_CUBES_SPLIT_IDS)

    all_ids = set()
    for faces in shared.values():
        all_ids |= set(faces)
    assert all_ids == set(range(1, len(all_ids) + 1))


def test_cadquery_backend_writes_one_shared_surface(tmp_path):
    """End to end: the interface is one surface bounding two volumes.

    Two touching boxes have 11 distinct faces. Without sharing, the interface
    is written twice and the file has 12 surfaces, none of which bounds two
    volumes.
    """
    pytest.importorskip("pymoab")

    model = CadToDagmc()
    model.add_cadquery_object(_two_touching_boxes(), material_tags=["mat1", "mat2"])
    h5m_filename = tmp_path / "touching_boxes.h5m"

    model.export_dagmc_h5m_file(
        filename=str(h5m_filename),
        meshing_backend="cadquery",
        tolerance=0.1,
        angular_tolerance=0.1,
    )

    surface_ids, shared = _surface_ids_and_shared_count(h5m_filename)
    assert len(surface_ids) == 11
    assert shared == 1


def test_three_solids_get_contiguous_surface_ids(tmp_path):
    """Three solids meeting on several faces must not inflate the id range.

    A gap left where a merged id was pushes the highest surface id above the
    surface count, and OpenMC then rejects the model because a DAGMC universe
    embedded in CSG shares an id space with the CSG surfaces.
    """
    pytest.importorskip("pymoab")

    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 7, 0)).box(10, 4, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 0, 7)).box(10, 10, 4))

    model = CadToDagmc()
    model.add_cadquery_object(assembly, material_tags=["mat1", "mat2", "mat3"])
    h5m_filename = tmp_path / "three_boxes.h5m"

    model.export_dagmc_h5m_file(
        filename=str(h5m_filename),
        meshing_backend="cadquery",
        tolerance=0.1,
        angular_tolerance=0.1,
    )

    surface_ids, shared = _surface_ids_and_shared_count(h5m_filename)
    assert surface_ids == list(range(1, len(surface_ids) + 1))
    assert shared == 2


def test_unimprinted_export_is_unaffected(tmp_path):
    """Without imprinting the solids are separate and share no face.

    The vertices are not welded either, so there is nothing to merge and the
    interface is legitimately written twice.
    """
    pytest.importorskip("pymoab")

    model = CadToDagmc()
    model.add_cadquery_object(_two_touching_boxes(), material_tags=["mat1", "mat2"])
    h5m_filename = tmp_path / "touching_boxes_unimprinted.h5m"

    model.export_dagmc_h5m_file(
        filename=str(h5m_filename),
        meshing_backend="cadquery",
        imprint=False,
        tolerance=0.1,
        angular_tolerance=0.1,
    )

    surface_ids, shared = _surface_ids_and_shared_count(h5m_filename)
    assert len(surface_ids) == 12
    assert shared == 0
