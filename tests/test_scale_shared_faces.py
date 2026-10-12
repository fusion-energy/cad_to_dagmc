"""Scaling must keep the faces imprinted solids share shared.

A small box sits on part of a big box's top face. Imprinting splits that face
and the contact patch becomes one face shared by both solids, which DAGMC needs
as a single surface with a sense for each volume. Scaling each solid on its own
gave each its own copy of that face, so geometry imprinted before it was
loaded, and exported with imprint=False, lost the shared surface whenever it
was scaled for the cad-to-dagmc-mesher backend.
"""

import cadquery as cq
import pytest

from cad_to_dagmc import CadToDagmc
from cad_to_dagmc.core import _scale_together, imprint_assembly


def _imprinted_boxes():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10, 10, 10))
    assembly.add(cq.Workplane().transformed(offset=(0, 0, 7)).box(4, 4, 4))
    imprinted, _ = imprint_assembly(assembly)
    # newer cadquery returns a plain Shape, which add_cadquery_object does not take
    return cq.Compound(imprinted.wrapped)


def _unique_faces(shapes):
    # Faces() only lists a face shared by two solids once
    return len(cq.Compound.makeCompound(shapes).Faces())


def test_imprinted_boxes_share_a_face():
    """Check the fixture: 6 + 6 faces plus the split ring, less the shared one."""
    solids = _imprinted_boxes().Solids()
    assert len(solids) == 2
    assert _unique_faces(solids) == 12


@pytest.mark.parametrize("scale_factor", [1.0, 2.0, 10.0])
def test_scale_together_keeps_shared_faces(scale_factor):
    solids = _imprinted_boxes().Solids()

    scaled = _scale_together(solids, scale_factor)

    assert _unique_faces(scaled) == _unique_faces(solids)


def test_scale_together_keeps_order_and_scales():
    solids = _imprinted_boxes().Solids()

    scaled = _scale_together(solids, 10.0)

    assert len(scaled) == len(solids)
    for original, result in zip(solids, scaled):
        assert result.Volume() == pytest.approx(original.Volume() * 1000)
    # the originals are left alone
    assert solids[0].Volume() == pytest.approx(1000)


def test_add_cadquery_object_scale_keeps_shared_faces():
    model = CadToDagmc()
    model.add_cadquery_object(
        _imprinted_boxes(), material_tags=["big", "small"], scale_factor=10.0
    )

    assert _unique_faces(model.parts) == 12


def _shared_surfaces(h5m_filename):
    pydagmc = pytest.importorskip("pydagmc")
    model = pydagmc.Model(str(h5m_filename))
    return [s for s in model.surfaces if s.forward_volume and s.reverse_volume]


@pytest.mark.parametrize("meshing_backend", ["cad-to-dagmc-mesher", "gmsh"])
@pytest.mark.parametrize("scale_at", ["export", "add"])
def test_pre_imprinted_geometry_scaled_has_one_shared_surface(
    tmp_path, meshing_backend, scale_at
):
    """End to end: imprint first, export with imprint=False, scale on the way."""
    pytest.importorskip("pydagmc")
    model = CadToDagmc()
    model.add_cadquery_object(
        _imprinted_boxes(),
        material_tags=["big", "small"],
        scale_factor=10.0 if scale_at == "add" else 1.0,
    )
    sizing = (
        {"tolerance": 1.0}
        if meshing_backend == "cad-to-dagmc-mesher"
        else {"max_mesh_size": 20.0}
    )
    h5m_filename = tmp_path / "dagmc.h5m"

    model.export_dagmc_h5m_file(
        filename=str(h5m_filename),
        meshing_backend=meshing_backend,
        imprint=False,
        scale_factor=10.0 if scale_at == "export" else 1.0,
        **sizing,
    )

    assert len(_shared_surfaces(h5m_filename)) == 1
