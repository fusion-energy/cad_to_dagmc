"""imprint_assembly imprints with cadquery's Assembly.imprint.

Assembly.imprint changes each part in place, so the imprinted solids stay in
the order the parts were added and material tags need no remapping.
"""

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import imprint_assembly


def _boxes(*placements):
    """One box per (x offset, edge length), each its own part."""
    assembly = cq.Assembly()
    for x, size in placements:
        assembly.add(cq.Workplane().transformed(offset=(x, 0, 0)).box(size, size, size))
    return assembly


def _shared_faces(compound):
    solids = compound.Solids()
    return sum(
        face.isSame(other)
        for i, solid in enumerate(solids)
        for later in solids[i + 1:]
        for face in solid.Faces()
        for other in later.Faces()
    )


def test_single_solid_skips_imprint(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("a single solid must not be imprinted")

    monkeypatch.setattr(cq.Assembly, "imprint", unexpected)
    shape = imprint_assembly(cq.Assembly().add(cq.Workplane().box(1, 1, 1), name="box"))
    assert len(shape.Solids()) == 1


def test_touching_solids_share_a_face():
    shape = imprint_assembly(_boxes((0, 10), (10, 10)))
    assert len(shape.Solids()) == 2
    assert len(shape.Faces()) == 11
    assert _shared_faces(shape) == 1


def test_solids_keep_the_order_parts_were_added():
    # added right to left with distinct sizes, so any reordering would show
    shape = imprint_assembly(_boxes((20, 10), (10, 10), (0, 10), (-7.5, 5)))
    assert [round(s.Center().x, 6) for s in shape.Solids()] == [20, 10, 0, -7.5]
    assert _shared_faces(shape) == 3


def test_a_part_touching_nothing_is_kept():
    shape = imprint_assembly(_boxes((0, 10), (50, 10)))
    assert [round(s.Center().x, 6) for s in shape.Solids()] == [0, 50]
    assert _shared_faces(shape) == 0


def test_touching_parts_and_a_separate_part():
    shape = imprint_assembly(_boxes((0, 10), (10, 10), (50, 10)))
    assert [round(s.Center().x, 6) for s in shape.Solids()] == [0, 10, 50]
    assert _shared_faces(shape) == 1


def test_overlapping_parts_are_rejected():
    with pytest.raises(ValueError, match="Overlapping solids in the CAD"):
        imprint_assembly(_boxes((0, 10), (5, 10)))


def test_gmsh_h5m_material_tags_follow_part_order(tmp_path):
    """Tags reach the right volumes when imprinting touches every solid."""
    di = pytest.importorskip("dagmc_h5m_file_inspector")
    model = CadToDagmc()
    model.add_cadquery_object(
        _boxes((20, 10), (10, 10), (0, 10)), material_tags=["right", "middle", "left"]
    )
    h5m = str(tmp_path / "ordered.h5m")
    model.export_dagmc_h5m_file(filename=h5m, meshing_backend="gmsh", max_mesh_size=5)
    assert di.get_volumes_and_materials(h5m) == {1: "right", 2: "middle", 3: "left"}
