"""Glue propagation, topology, and compatibility at the CadQuery imprint boundary."""

import inspect

import cadquery as cq
import gmsh
import pytest
from OCP.BOPAlgo import BOPAlgo_GlueEnum
from test_imprint_threads import (
    GLUES,
    IMPRINT_MODES,
    IMPRINT_PATHS,
    _assert_outputs,
    _export,
    _model,
    _pool_threads,
    _two_touching_boxes,
)
from test_imprint_threads import (
    imprint_calls as imprint_calls,  # noqa: PLC0414 - shared pytest fixture
)

from cad_to_dagmc.core import (
    _mesh_with_cad_to_dagmc_mesher,
    imprint_assembly,
)

pytestmark = pytest.mark.filterwarnings("error::UserWarning")


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("imprint", IMPRINT_MODES)
def test_every_export_passes_scalar_mode_and_thread_limit(tmp_path, imprint_calls, path, imprint):
    before = _pool_threads()
    _export(path, _model(), tmp_path, imprint, imprint_threads=1)
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    # Explicit None still imprints (GlueOff); only literal False disables it.
    assert imprint_calls == ([] if imprint is False else [(1, imprint)])
    _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("imprint", IMPRINT_MODES)
def test_single_solid_exports_skip_imprint_for_all_modes(tmp_path, imprint_calls, path, imprint):
    before = _pool_threads()
    _export(path, _model(single_solid=True), tmp_path, imprint, imprint_threads=1)
    assert imprint_calls == []
    assert _pool_threads() == before
    _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("glue", GLUES)
def test_glue_and_thread_limit_reach_assembly_imprint(monkeypatch, glue):
    calls = []

    def imprint(self, *, glue="partial"):
        calls.append(glue)
        assert _pool_threads() == 1
        return self

    monkeypatch.setattr(cq.Assembly, "imprint", imprint)
    before = _pool_threads()
    imprint_assembly(_two_touching_boxes(), threads=1, glue=glue)
    assert calls == [glue]
    assert _pool_threads() == before


@pytest.mark.parametrize("glue", ["off", "Partial", True, False, 0, 1, [], {}])
def test_low_level_imprint_rejects_invalid_glue(glue):
    with pytest.raises(ValueError, match="imprint"):
        imprint_assembly(_two_touching_boxes(), glue=glue)


def test_imprint_error_restores_thread_pool(monkeypatch):
    def failing(self, *, glue=None):
        assert _pool_threads() == 1
        raise RuntimeError("imprint failed")

    monkeypatch.setattr(cq.Assembly, "imprint", failing)
    before = _pool_threads()
    with pytest.raises(RuntimeError, match="imprint failed"):
        imprint_assembly(_two_touching_boxes(), threads=1, glue="partial")
    assert _pool_threads() == before


@pytest.mark.parametrize("options, mode", [
    ({}, BOPAlgo_GlueEnum.BOPAlgo_GlueShift),
    ({"glue": "partial"}, BOPAlgo_GlueEnum.BOPAlgo_GlueShift),
    ({"glue": "full"}, BOPAlgo_GlueEnum.BOPAlgo_GlueFull),
    ({"glue": None}, BOPAlgo_GlueEnum.BOPAlgo_GlueOff),
], ids=["omitted-default", "partial", "full", "explicit-none"])
def test_modern_imprint_uses_actual_occ_glue_enum(monkeypatch, options, mode):
    real_set_glue, builders = cq.occ_impl.shapes._set_glue, []

    def recording_set_glue(builder, glue):
        builders.append(builder)
        real_set_glue(builder, glue)

    monkeypatch.setattr(cq.occ_impl.shapes, "_set_glue", recording_set_glue)
    imprint_assembly(_two_touching_boxes(), **options)
    assert len(builders) == 1
    assert builders[0].Glue() == mode

def test_default_glue_is_partial(imprint_calls):
    imprint_assembly(_two_touching_boxes())
    assert [glue for _, glue in imprint_calls] == ["partial"]


@pytest.mark.parametrize("partial_contact, glue, faces, volumes, shared", [
    (False, "partial", 11, [1000, 1000], 1), (False, "full", 11, [1000, 1000], 1),
    (False, None, 11, [1000, 1000], 1), (True, "partial", 12, [64, 1000], 1),
    (True, None, 12, [64, 1000], 1),
    # full glue only merges exactly coincident faces, so a partly coincident
    # contact is left unsplit and nothing is shared
    (True, "full", 12, [64, 1000], 0),
])
def test_full_and_partial_face_contact_topology(
    partial_contact, glue, faces, volumes, shared
):
    assembly = _two_touching_boxes()
    if partial_contact:
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(10, 10, 10))
        assembly.add(cq.Workplane().transformed(offset=(0, 0, 7)).box(4, 4, 4))
    shape = imprint_assembly(assembly, glue=glue)
    assert len(shape.Solids()) == 2
    assert len(shape.Faces()) == faces
    assert sorted(solid.Volume() for solid in shape.Solids()) == pytest.approx(volumes)
    left, right = shape.Solids()
    assert sum(
        face.isSame(other) for face in left.Faces() for other in right.Faces()
    ) == shared


@pytest.mark.parametrize("imprint, imprint_threads", [
    ("partial", "all"), ("full", 3), (None, 1), (False, "all"), (False, 2),
])
def test_mesher_adapter_forwards_raw_scalar_arguments(monkeypatch, imprint, imprint_threads):
    cad = pytest.importorskip("cad_to_dagmc_mesher.cad")
    calls = []
    real_imprint, before = cq.occ_impl.assembly.imprint, _pool_threads()

    def mesh_assembly(assembly, *, solid_config, imprint, imprint_threads):
        assert cq.occ_impl.assembly.imprint is real_imprint
        assert _pool_threads() == before
        calls.append((imprint, imprint_threads))
        return {"vertices": [], "triangles_by_solid_by_face": {},
                "material_tags": [config.name for config in solid_config]}

    monkeypatch.setattr(cad, "mesh_assembly", mesh_assembly)
    _mesh_with_cad_to_dagmc_mesher(
        _two_touching_boxes(), ["left", "right"], 1.0, 0.3,
        tet_volumes=None, target_edge_length=None, imprint=imprint,
        imprint_threads=imprint_threads,
    )
    assert calls == [(imprint, imprint_threads)]
    assert cq.occ_impl.assembly.imprint is real_imprint
    assert _pool_threads() == before


def test_mesher_adapter_has_separate_threads_but_no_glue_keyword():
    parameters = inspect.signature(_mesh_with_cad_to_dagmc_mesher).parameters
    assert "imprint" in parameters
    assert parameters["imprint_threads"].default == "all"
    assert not {"glue", "imprint_glue"} & parameters.keys()
