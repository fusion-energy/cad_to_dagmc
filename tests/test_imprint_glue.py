"""Glue propagation, topology, and compatibility at the CadQuery imprint boundary."""

import inspect
from contextlib import nullcontext
from types import MappingProxyType

import cadquery as cq
import gmsh
import pytest
from OCP.BOPAlgo import BOPAlgo_GlueEnum
from test_imprint_threads import (
    GLUES,
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
    DEFAULT_IMPRINT,
    _mesh_with_cad_to_dagmc_mesher,
    imprint_assembly,
)

HAS_GLUE = "glue" in inspect.signature(cq.occ_impl.assembly.imprint).parameters
pytestmark = pytest.mark.filterwarnings("error::UserWarning")


def _expected_response(glue):
    if not HAS_GLUE and glue != "partial":
        return pytest.raises(RuntimeError, match="legacy imprint always uses partial glue")
    return nullcontext()


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("glue", GLUES)
def test_every_export_passes_glue_and_thread_limit(tmp_path, imprint_calls, path, glue):
    options = {"threads": 1, "glue": glue}
    original, before = options.copy(), _pool_threads()
    with _expected_response(glue):
        _export(path, _model(), tmp_path, options)
    assert options == original
    assert _pool_threads() == before
    assert not gmsh.isInitialized()
    if not HAS_GLUE and glue != "partial":
        assert imprint_calls == []
        assert not list(tmp_path.iterdir()), "unsupported glue must not create outputs"
    else:
        assert imprint_calls == [(1, glue if HAS_GLUE else "legacy")]
        _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("imprint", [False, *({"threads": 1, "glue": glue} for glue in GLUES)],
                         ids=["disabled", "single-partial", "single-full", "single-off"])
def test_disabled_and_single_solid_exports_skip_imprint(tmp_path, imprint_calls, path, imprint):
    original = dict(imprint) if imprint is not False else False
    before = _pool_threads()
    _export(path, _model(single_solid=imprint is not False), tmp_path, imprint)
    assert imprint_calls == []
    assert imprint == original
    assert _pool_threads() == before
    _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("path", IMPRINT_PATHS)
def test_every_export_accepts_read_only_mapping(tmp_path, path):
    options = MappingProxyType({"threads": 1, "glue": "partial"})
    before = _pool_threads()
    _export(path, _model(), tmp_path, options)
    assert dict(options) == {"threads": 1, "glue": "partial"}
    assert _pool_threads() == before
    _assert_outputs(path, tmp_path)


@pytest.mark.parametrize("path", IMPRINT_PATHS)
@pytest.mark.parametrize("glue", ["full", None])
def test_legacy_signature_rejects_unsupported_glue_without_outputs(tmp_path, monkeypatch, path, glue):
    calls = []

    def legacy(assembly):
        calls.append(assembly)
        raise AssertionError("unsupported glue reached legacy imprint")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", legacy)
    options = {"threads": "all", "glue": glue}
    original, before = options.copy(), _pool_threads()
    with pytest.raises(RuntimeError, match="legacy imprint always uses partial glue"):
        _export(path, _model(), tmp_path, options)
    assert calls == []
    assert options == original
    assert _pool_threads() == before
    assert cq.occ_impl.assembly.imprint is legacy
    assert not gmsh.isInitialized()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("supports_glue", [False, True])
@pytest.mark.parametrize("glue", GLUES)
def test_modern_and_legacy_signatures(monkeypatch, supports_glue, glue):
    calls, sentinel = [], object()

    def modern(assembly, *, glue="partial"):
        calls.append(glue)
        assert _pool_threads() == 1
        return sentinel

    def legacy(assembly):
        return modern(assembly, glue="legacy")

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", modern if supports_glue else legacy)
    before = _pool_threads()
    if not supports_glue and glue != "partial":
        with pytest.raises(RuntimeError, match="legacy imprint always uses partial glue"):
            imprint_assembly(_two_touching_boxes(), threads=1, glue=glue)
        assert calls == []
    else:
        assert imprint_assembly(_two_touching_boxes(), threads=1, glue=glue) is sentinel
        assert calls == [glue if supports_glue else "legacy"]
    assert _pool_threads() == before


@pytest.mark.parametrize("supports_glue", [False, True])
def test_imprint_error_restores_thread_pool(monkeypatch, supports_glue):
    def modern(assembly, *, glue=None):
        assert _pool_threads() == 1
        raise RuntimeError("imprint failed")

    def legacy(assembly):
        return modern(assembly)

    monkeypatch.setattr(cq.occ_impl.assembly, "imprint", modern if supports_glue else legacy)
    before = _pool_threads()
    with pytest.raises(RuntimeError, match="imprint failed"):
        imprint_assembly(_two_touching_boxes(), threads=1, glue="partial")
    assert _pool_threads() == before


@pytest.mark.skipif(not HAS_GLUE, reason="legacy imprint has no selectable glue API")
@pytest.mark.parametrize("glue, mode", [
    ("partial", BOPAlgo_GlueEnum.BOPAlgo_GlueShift),
    ("full", BOPAlgo_GlueEnum.BOPAlgo_GlueFull),
    (None, BOPAlgo_GlueEnum.BOPAlgo_GlueOff),
])
def test_modern_imprint_uses_actual_occ_glue_enum(monkeypatch, glue, mode):
    real_builder, builders = cq.occ_impl.assembly.BOPAlgo_Builder, []

    def recording_builder():
        builder = real_builder()
        builders.append(builder)
        return builder

    monkeypatch.setattr(cq.occ_impl.assembly, "BOPAlgo_Builder", recording_builder)
    imprint_assembly(_two_touching_boxes(), glue=glue)
    assert len(builders) == 1
    assert builders[0].Glue() == mode


def test_default_glue_is_partial(imprint_calls):
    imprint_assembly(_two_touching_boxes())
    assert [glue for _, glue in imprint_calls] == ["partial" if HAS_GLUE else "legacy"]


@pytest.mark.parametrize("partial_contact, glue, faces, volumes", [
    (False, "partial", 11, [1000, 1000]), (False, "full", 11, [1000, 1000]),
    (False, None, 11, [1000, 1000]), (True, "partial", 12, [64, 1000]),
    (True, None, 12, [64, 1000]),
])
def test_full_and_partial_face_contact_topology(partial_contact, glue, faces, volumes):
    assembly = _two_touching_boxes()
    if partial_contact:
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(10, 10, 10))
        assembly.add(cq.Workplane().transformed(offset=(0, 0, 7)).box(4, 4, 4))
    with _expected_response(glue):
        shape, _ = imprint_assembly(assembly, glue=glue)
    if not HAS_GLUE and glue != "partial":
        return
    assert len(shape.Solids()) == 2
    assert len(shape.Faces()) == faces
    assert sorted(solid.Volume() for solid in shape.Solids()) == pytest.approx(volumes)
    left, right = shape.Solids()
    assert sum(face.isSame(other) for face in left.Faces() for other in right.Faces()) == 1


@pytest.mark.parametrize("imprint", [
    False, DEFAULT_IMPRINT, {"threads": 1, "glue": None},
    MappingProxyType({"threads": "all", "glue": "full"}),
], ids=["disabled", "default", "dict", "mapping-proxy"])
def test_mesher_adapter_forwards_original_mapping_or_false(monkeypatch, imprint):
    cad = pytest.importorskip("cad_to_dagmc_mesher.cad")
    calls = []
    original = dict(imprint) if imprint is not False else False
    real_imprint, before = cq.occ_impl.assembly.imprint, _pool_threads()

    def mesh_assembly(assembly, *, solid_config, imprint):
        assert cq.occ_impl.assembly.imprint is real_imprint
        assert _pool_threads() == before
        calls.append(imprint)
        return {"vertices": [], "triangles_by_solid_by_face": {},
                "material_tags": [config.name for config in solid_config]}

    monkeypatch.setattr(cad, "mesh_assembly", mesh_assembly)
    _mesh_with_cad_to_dagmc_mesher(
        _two_touching_boxes(), ["left", "right"], 1.0, 0.3,
        tet_volumes=None, target_edge_length=None, imprint=imprint,
    )
    assert len(calls) == 1
    assert calls[0] is imprint, "the adapter must not copy, resolve, or translate imprint"
    assert imprint == original
    assert cq.occ_impl.assembly.imprint is real_imprint
    assert _pool_threads() == before


def test_mesher_adapter_has_no_separate_imprint_arguments():
    parameters = inspect.signature(_mesh_with_cad_to_dagmc_mesher).parameters
    assert "imprint" in parameters
    assert not {"glue", "imprint_threads", "imprint_glue"} & parameters.keys()
